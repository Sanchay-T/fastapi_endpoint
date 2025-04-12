from django.shortcuts import render
from django.db import connection
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status, viewsets, filters
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
import datetime
import redis
import json
from celery.result import AsyncResult
import pandas as pd
import os
import logging
import time
from django.http import HttpResponse
import math  # Import math for sanitization

from .models import ApiKey, ScheduledTask
from .serializers import (
    UserSerializer,
    ApiKeySerializer,
    ScheduledTaskSerializer,
    HealthCheckSerializer,
    BankStatementAnalysisRequestSerializer,
    ExcelDownloadRequestSerializer,
)
from backend.celery import app as celery_app
from statement_analyzer.tax_professional.banks.CA_Statement_Analyzer import (
    start_extraction_add_pdf,
    save_to_excel,
)
from statement_analyzer.account_number_ifsc_extraction import extract_accno_ifsc
from statement_analyzer.pdf_to_name import extract_entities

# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint that verifies the system components are operational.
    This endpoint is exempt from authentication to allow for monitoring tools.
    """
    health_data = {
        "status": "ok",
        "timestamp": datetime.datetime.now().isoformat(),
        "components": {
            "database": False,
            "redis": False,
        },
        "info": {
            "version": "1.0.0",
            "environment": settings.DEBUG and "development" or "production",
        },
    }

    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_data["components"]["database"] = True
    except Exception as e:
        health_data["components"]["database"] = False
        health_data["status"] = "error"
        health_data["errors"] = {"database": str(e)}

    # Check Redis if configured
    try:
        if (
            hasattr(settings, "CACHES")
            and settings.CACHES.get("default", {}).get("BACKEND")
            == "django_redis.cache.RedisCache"
        ):
            redis_url = settings.CACHES["default"]["LOCATION"]
            r = redis.from_url(redis_url)
            r.ping()
            health_data["components"]["redis"] = True
    except Exception as e:
        health_data["components"]["redis"] = False
        health_data["status"] = "error"
        if not health_data.get("errors"):
            health_data["errors"] = {}
        health_data["errors"]["redis"] = str(e)

    # Return appropriate HTTP status code based on health
    response_status = (
        status.HTTP_200_OK
        if health_data["status"] == "ok"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(health_data, status=response_status)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing and retrieving users.
    Only accessible to admins.
    """

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "date_joined"]


class ApiKeyViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing API keys.
    """

    serializer_class = ApiKeySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at", "expires_at"]

    def get_queryset(self):
        """Filter API keys to show only those belonging to the current user or all keys for admins."""
        user = self.request.user
        if user.is_staff:
            return ApiKey.objects.all()
        return ApiKey.objects.filter(user=user)

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Regenerate the API key."""
        api_key = self.get_object()
        api_key.key = api_key.generate_key()
        api_key.save(update_fields=["key"])
        return Response(
            {"message": "API key regenerated successfully", "key": api_key.key}
        )


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing scheduled tasks.
    """

    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status"]
    search_fields = ["name"]
    ordering_fields = ["name", "scheduled_at", "status"]

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel the task if it hasn't started yet."""
        task = self.get_object()
        if task.status == "pending":
            if task.task_id:
                celery_app.control.revoke(task.task_id, terminate=True)
            task.status = "cancelled"
            task.save(update_fields=["status"])
            return Response({"message": "Task cancelled successfully"})
        return Response(
            {"message": f"Cannot cancel task with status {task.status}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Get the current status of a task."""
        task = self.get_object()
        result = None

        if task.task_id:
            # Get the task result from Celery
            async_result = AsyncResult(task.task_id)

            if async_result.state == "PENDING":
                task.status = "pending"
            elif async_result.state == "STARTED":
                task.status = "running"
                if not task.started_at:
                    task.started_at = timezone.now()
            elif async_result.state == "SUCCESS":
                task.status = "completed"
                task.result = async_result.result
                if not task.completed_at:
                    task.completed_at = timezone.now()
            elif async_result.state == "FAILURE":
                task.status = "failed"
                task.error_message = str(async_result.result)
                if not task.completed_at:
                    task.completed_at = timezone.now()

            task.save()

        return Response(
            {
                "task_id": task.task_id,
                "status": task.status,
                "scheduled_at": task.scheduled_at,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
                "result": task.result,
                "error_message": task.error_message,
            }
        )


# -------------------------------------------
# Bank Statement Analysis Views
# -------------------------------------------

logger = logging.getLogger(__name__)


def sanitize_data_for_json(data):
    """Recursively replace NaN, Infinity, -Infinity in dicts/lists with None."""
    if isinstance(data, dict):
        return {k: sanitize_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data_for_json(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None  # Replace non-compliant floats with None (JSON null)
        return data
    else:
        return data


class BankStatementAnalysisView(APIView):
    """View to handle bank statement analysis requests."""

    permission_classes = [IsAuthenticated]  # Or adjust as needed

    def post(self, request, *args, **kwargs):
        logger.info("Received request for bank statement analysis.")
        serializer = BankStatementAnalysisRequestSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            logger.info(
                f"Analysis request validated for ca_id: {validated_data['ca_id']}"
            )

            try:
                # --- Mimic logic from FastAPI endpoint ---
                bank_names = validated_data["bank_names"]
                pdf_paths = validated_data["pdf_paths"]
                passwords = validated_data.get("passwords", [])  # Default to empty list
                start_date = validated_data["start_date"]
                end_date = validated_data["end_date"]
                ca_id = validated_data["ca_id"]
                # whole_transaction_sheet_data = validated_data.get('whole_transaction_sheet')
                # aiyazs_array_of_array_data = validated_data.get('aiyazs_array_of_array')

                # 1. NER Processing (Simplified for sync execution)
                ner_results = {"Name": [], "Acc Number": []}
                logger.info(f"Starting NER processing for {len(pdf_paths)} PDFs.")
                start_ner = time.time()
                person_count = 0
                for pdf_path in pdf_paths:
                    person_count += 1
                    fetched_name = None
                    fetched_acc_num = None
                    try:
                        logger.debug(f"Processing NER for PDF: {pdf_path}")
                        name_entities = extract_entities(pdf_path)
                        acc_number_ifsc = extract_accno_ifsc(pdf_path)
                        logger.debug(
                            f"NER Results - Names: {name_entities}, Acc/IFSC: {acc_number_ifsc}"
                        )

                        fetched_acc_num = acc_number_ifsc.get("acc")
                        if name_entities:
                            # Simple logic: take the first entity as name
                            fetched_name = name_entities[0] if name_entities else None

                        ner_results["Name"].append(
                            fetched_name or f"Statement {person_count}"
                        )
                        ner_results["Acc Number"].append(
                            fetched_acc_num or "XXXXXXXXXXX"
                        )
                    except Exception as ner_err:
                        logger.error(
                            f"Error during NER processing for {pdf_path}: {ner_err}"
                        )
                        ner_results["Name"].append(f"Statement {person_count} (Error)")
                        ner_results["Acc Number"].append("XXXXXXXXXXX (Error)")
                        # Optionally, decide if the whole process should fail here
                        # raise ner_err # Uncomment to fail fast

                end_ner = time.time()
                logger.info(
                    f"NER processing completed in {end_ner - start_ner:.2f} seconds."
                )
                logger.debug(f"Final NER results: {ner_results}")

                # 2. Main Extraction
                # Note: progress_data is simplified/omitted for sync execution
                # TODO: Handle whole_transaction_sheet and aiyazs_array_of_array properly if needed
                whole_transaction_sheet = None  # Placeholder
                aiyazs_array_of_array = None  # Placeholder
                # if whole_transaction_sheet_data:
                #     whole_transaction_sheet = pd.DataFrame(whole_transaction_sheet_data)
                #     # ... date conversion needed ...
                # if aiyazs_array_of_array_data:
                # ... conversion needed ...

                logger.info("Starting main statement extraction...")
                start_extraction = time.time()
                analysis_result = start_extraction_add_pdf(
                    bank_names,
                    pdf_paths,
                    passwords,
                    start_date,
                    end_date,
                    ca_id,
                    progress_data=None,  # No progress tracking in sync view yet
                    whole_transaction_sheet=whole_transaction_sheet,
                    aiyazs_array_of_array=aiyazs_array_of_array,
                )
                end_extraction = time.time()
                logger.info(
                    f"Main extraction completed in {end_extraction - start_extraction:.2f} seconds."
                )
                logger.debug(
                    f"Raw analysis result keys: {analysis_result.keys() if analysis_result else 'None'}"
                )

                # --- Sanitize the result before sending ---
                sanitized_analysis_result = sanitize_data_for_json(analysis_result)
                # --- End sanitization ---

                # 3. Format Response using SANITIZED data
                response_data = {
                    "status": "success",
                    "message": "Bank statements analyzed successfully (sync)",
                    "data": sanitized_analysis_result.get(
                        "sheets_in_json"
                    ),  # Check key name
                    "pdf_paths_not_extracted": sanitized_analysis_result.get(
                        "pdf_paths_not_extracted"
                    ),
                    "ner_results": sanitize_data_for_json(
                        ner_results
                    ),  # Sanitize NER results too
                    "success_page_number": sanitized_analysis_result.get(
                        "success_page_number"
                    ),
                    "missing_months_list": sanitized_analysis_result.get(
                        "missing_months_list"
                    ),
                }
                logger.info(f"Analysis successful for ca_id: {ca_id}")
                return Response(response_data, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(
                    f"Error processing bank statements for ca_id {validated_data.get('ca_id', 'N/A')}: {str(e)}",
                    exc_info=True,
                )
                return Response(
                    {
                        "status": "error",
                        "message": f"Error processing bank statements: {str(e)}",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.warning(f"Analysis request failed validation: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BankStatementExcelDownloadView(APIView):
    """View to handle Excel download requests."""

    permission_classes = [IsAuthenticated]  # Or adjust as needed

    def post(self, request, *args, **kwargs):
        logger.info("Received request for Excel download.")
        serializer = ExcelDownloadRequestSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            case_name = validated_data["case_name"]
            logger.info(f"Excel download request validated for case: {case_name}")

            try:
                transaction_data = validated_data["transaction_data"]
                name_n_num_data = validated_data["name_n_num"]

                # Convert list of dicts to DataFrames
                logger.debug(
                    f"Converting transaction data ({len(transaction_data)} records) to DataFrame."
                )
                transaction_df = pd.DataFrame(transaction_data)
                logger.debug(
                    f"Converting name/number data ({len(name_n_num_data)} records) to DataFrame."
                )
                name_n_num_df = pd.DataFrame(name_n_num_data)

                # Call the function to save the excel file
                logger.info(f"Calling save_to_excel for case: {case_name}")
                start_excel = time.time()
                file_path = save_to_excel(transaction_df, name_n_num_df, case_name)
                end_excel = time.time()
                logger.info(
                    f"save_to_excel completed in {end_excel - start_excel:.2f} seconds. File path: {file_path}"
                )

                if not file_path or not os.path.exists(file_path):
                    logger.error(
                        f"save_to_excel did not return a valid path or file does not exist: {file_path}"
                    )
                    raise FileNotFoundError(
                        "Excel file could not be generated or found."
                    )

                # Read the file content
                logger.info(f"Reading content from generated Excel file: {file_path}")
                with open(file_path, "rb") as excel_file:
                    file_content = excel_file.read()

                # Create HTTP response
                response = HttpResponse(
                    file_content,
                    content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
                response["Content-Disposition"] = (
                    f'attachment; filename="{os.path.basename(file_path)}'
                )
                logger.info(
                    f"Successfully prepared Excel file download response for case: {case_name}"
                )

                # Clean up the generated file? Optional, depends on requirements.
                # try:
                #     os.remove(file_path)
                #     logger.info(f"Cleaned up temporary Excel file: {file_path}")
                # except OSError as e:
                #     logger.error(f"Error removing temporary Excel file {file_path}: {e}")

                return response

            except Exception as e:
                logger.error(
                    f"Error generating Excel file for case {case_name}: {str(e)}",
                    exc_info=True,
                )
                return Response(
                    {
                        "status": "error",
                        "message": f"Error generating Excel file: {str(e)}",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.warning(
                f"Excel download request failed validation: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
