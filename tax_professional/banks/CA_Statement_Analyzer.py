import shutil
import os
from lib2to3.pytree import convert
from openpyxl.styles import Font
import logging
from openpyxl import Workbook, load_workbook
import sys
import json
import pandas as pd
bold_font = Font(bold=True)
pd.options.display.float_format = "{:,.2f}".format
pd.set_option("display.max_columns", None)
pd.set_option("display.max_rows", None)
pd.set_option("display.width", None)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from common_functions import (process_excel_to_json,process_name_n_num_df,category_add_ca,
                              another_method,eod,opening_and_closing_bal,summary_sheet,
                              transaction_sheet,total_investment,redemption_investment,
                              creditor_list,debtor_list, cash_withdraw, cash_depo, div_int, emi,
                              refund_reversal, suspense_credit, suspense_debit, payment,receipt,
                              calculate_fixed_day_average, process_avg_last_6_months, extraction_process,
                              color_summary_sheet, format_numbers_with_commas, adjust_column_widths_for_varied_sheets,
                              Summary_note, Investment_note, CreditorList_note, DebtorList_note, CashWithdrawalt_note,
                              Cash_Deposit_note, Emi_note, Refund_note, Suspense_Credit_note, Suspense_Debit_note,
                              add_filters_to_excel, create_excel_sheet, color_excel_tabs_inplace, sort_dataframes_by_date,
                              extraction_process_explicit_lines)

def reconstruct_dict_from_json_save_to_excel(json_input, account_number, CA_ID):
    """
    Reconstructs the results dictionary from a JSON object.

    Args:
        json_input (str): A JSON-formatted string representing the results.

    Returns:
        dict: A dictionary where each key is a category and each value is a DataFrame.
    """
    # Parse the JSON string into a Python dictionary
    parsed_data = json.loads(json_input)

    # Initialize an empty dictionary to hold the DataFrames
    results = {}

    # Iterate through each key-value pair in the parsed data
    for key, records in parsed_data.items():
        # Convert the list of records into a Pandas DataFrame
        results[key] = pd.DataFrame(records)

    # Reconstruct all the DataFrames from the results dictionary
    name_n_num_df = results["Name Acc No"]
    particulars_df = results["Particulars"]
    income_receipts_df = results["Income Receipts"]
    imp_expenses_payments_df = results["Important Expenses"]
    other_expenses_df = results["Other Expenses"]
    loan_value_df = results["Opportunity to Earn"]
    transaction_sheet_df = results["Transactions"]
    eod_sheet_df = results["EOD"]
    investment_df = results["Investment"]
    creditor_df = results["Creditors"]
    debtor_df = results["Debtors"]
    upi_cr_df = results["UPI-CR"]
    upi_dr_df = results["UPI-DR"]
    cash_withdrawal_df = results["Cash Withdrawal"]
    cash_deposit_df = results["Cash Deposit"]
    dividend_int_df = results["Redemption, Dividend & Interest"]
    emi_df = results["Probable EMI"]
    refund_df = results["Refund-Reversal"]
    suspense_credit_df = results["Suspense Credit"]
    suspense_debit_df = results["Suspense Debit"]
    payment_df = results["Payment Voucher"]
    receipt_df = results["Receipt Voucher"]

    # All sheets are now restored as Pandas DataFrames

    filename = os.path.join(
        "saved_excel",
        f"{CA_ID}_extracted_statements_file_{account_number}.xlsx",
    )

    writer = pd.ExcelWriter(filename, engine="xlsxwriter")

    #start converting to excel
    sheet_name = "Summary"
    name_n_num_df.to_excel(writer, sheet_name=sheet_name, index=False)

    particulars_df.to_excel(
        writer,
        sheet_name=sheet_name,
        startrow=name_n_num_df.shape[0] + 2,
        index=False,
    )
    income_receipts_df.to_excel(
        writer,
        sheet_name=sheet_name,
        startrow=name_n_num_df.shape[0] + particulars_df.shape[0] + 4,
        index=False,
    )
    imp_expenses_payments_df.to_excel(
        writer,
        sheet_name=sheet_name,
        startrow=name_n_num_df.shape[0]
                 + particulars_df.shape[0]
                 + income_receipts_df.shape[0]
                 + 6,
        index=False,
    )
    other_expenses_df .to_excel(
        writer,
        sheet_name=sheet_name,
        startrow=name_n_num_df.shape[0]
                 + particulars_df.shape[0]
                 + income_receipts_df.shape[0]
                 + imp_expenses_payments_df.shape[0]
                 + 8,
        index=False,
    )

    loan_value_df.to_excel(writer, sheet_name='Opportunity to Earn', index=False)
    transaction_sheet_df.to_excel(writer, sheet_name='Transactions', index=False)
    eod_sheet_df.to_excel(writer, sheet_name='EOD', index=False)
    investment_df.to_excel(writer, sheet_name='Investment', index=False)
    creditor_df.to_excel(writer, sheet_name='Creditors', index=False)
    debtor_df.to_excel(writer, sheet_name='Debtors', index=False)
    upi_cr_df.to_excel(writer, sheet_name='UPI-CR', index=False)
    upi_dr_df.to_excel(writer, sheet_name='UPI-DR', index=False)
    cash_withdrawal_df.to_excel(writer, sheet_name='Cash Withdrawal', index=False)
    cash_deposit_df.to_excel(writer, sheet_name='Cash Deposit', index=False)
    dividend_int_df.to_excel(writer, sheet_name='Redemption, Dividend & Interest', index=False)
    emi_df.to_excel(writer, sheet_name='Probable EMI', index=False)
    refund_df.to_excel(writer, sheet_name='Refund-Reversal', index=False)
    suspense_credit_df.to_excel(writer, sheet_name='Suspense Credit', index=False)
    suspense_debit_df.to_excel(writer, sheet_name='Suspense Debit', index=False)
    payment_df.to_excel(writer, sheet_name='Payment Voucher', index=False)
    receipt_df.to_excel(writer, sheet_name='Receipt Voucher', index=False)
    writer._save()
    writer.close()
    return filename


def returns_json_output_of_all_sheets(df, name_n_num_df):
    # Generate all necessary DataFrames
    eod_sheet_df = eod(df)
    opening_bal, closing_bal = opening_and_closing_bal(eod_sheet_df, df)

    summary_df_list = summary_sheet(df, opening_bal, closing_bal, df)

    particulars_df = summary_df_list[0]
    income_receipts_df = summary_df_list[1]
    imp_expenses_payments_df = summary_df_list[2]
    other_expenses_df = summary_df_list[3]

    df['Value Date'] = pd.to_datetime(df['Value Date']).dt.strftime('%d-%m-%Y')
    transaction_sheet_df = transaction_sheet(df)
    investment_df = total_investment(df)
    creditor_df = creditor_list(df)
    debtor_df = debtor_list(transaction_sheet_df)

    upi_cr_df = df[(df["Description"].str.contains("UPI", case=False)) & (df["Credit"] > 0)]
    upi_dr_df = df[(df["Description"].str.contains("UPI", case=False)) & (df["Debit"] > 0)]

    cash_withdrawal_df = cash_withdraw(df)
    cash_deposit_df = cash_depo(df)
    dividend_int_df = div_int(df)
    emi_df = emi(df)
    refund_df = refund_reversal(df)
    suspense_credit_df = suspense_credit(df)
    suspense_debit_df = suspense_debit(df)
    payment_df = payment(df)
    receipt_df = receipt(df)

    bank_avg_balance_df = calculate_fixed_day_average(eod_sheet_df)
    loan_value_df = process_avg_last_6_months(bank_avg_balance_df, eod_sheet_df)

    # Build a dictionary to hold the labeled DataFrames
    result_dict = {
        "Name Acc No": name_n_num_df.to_dict(orient="records"),
        "Particulars": particulars_df.to_dict(orient="records"),
        "Income Receipts": income_receipts_df.to_dict(orient="records"),
        "Important Expenses": imp_expenses_payments_df.to_dict(orient="records"),
        "Other Expenses": other_expenses_df.to_dict(orient="records"),
        "Opportunity to Earn": loan_value_df.to_dict(orient="records"),
        "Transactions": transaction_sheet_df.to_dict(orient="records"),
        "EOD": eod_sheet_df.to_dict(orient="records"),
        "Investment": investment_df.to_dict(orient="records"),
        "Creditors": creditor_df.to_dict(orient="records"),
        "Debtors": debtor_df.to_dict(orient="records"),
        "UPI-CR": upi_cr_df.to_dict(orient="records"),
        "UPI-DR": upi_dr_df.to_dict(orient="records"),
        "Cash Withdrawal": cash_withdrawal_df.to_dict(orient="records"),
        "Cash Deposit": cash_deposit_df.to_dict(orient="records"),
        "Redemption, Dividend & Interest": dividend_int_df.to_dict(orient="records"),
        "Probable EMI": emi_df.to_dict(orient="records"),
        "Refund-Reversal": refund_df.to_dict(orient="records"),
        "Suspense Credit": suspense_credit_df.to_dict(orient="records"),
        "Suspense Debit": suspense_debit_df.to_dict(orient="records"),
        "Payment Voucher": payment_df.to_dict(orient="records"),
        "Receipt Voucher": receipt_df.to_dict(orient="records"),
    }

    # Convert the entire dictionary to JSON
    json_output = json.dumps(result_dict, indent=4)
    with open("new_output.json", "w") as file:
        file.write(json_output)
    return json_output


def refresh_category_all_sheets(df, eod_sheet_df):

    opening_bal, closing_bal = opening_and_closing_bal(eod_sheet_df, df)

    summary_df_list = summary_sheet(df, opening_bal, closing_bal, df)

    particulars_df = summary_df_list[0]
    income_receipts_df = summary_df_list[1]
    imp_expenses_payments_df = summary_df_list[2]
    other_expenses_df = summary_df_list[3]

    df['Value Date'] = pd.to_datetime(df['Value Date']).dt.strftime('%d-%m-%Y')
    transaction_sheet_df = transaction_sheet(df)
    investment_df = total_investment(df)
    creditor_df = creditor_list(df)
    debtor_df = debtor_list(transaction_sheet_df)

    upi_cr_df = df[(df["Description"].str.contains("UPI", case=False)) & (df["Credit"] > 0)]
    upi_dr_df = df[(df["Description"].str.contains("UPI", case=False)) & (df["Debit"] > 0)]

    cash_withdrawal_df = cash_withdraw(df)
    cash_deposit_df = cash_depo(df)
    dividend_int_df = div_int(df)
    emi_df = emi(df)
    refund_df = refund_reversal(df)
    suspense_credit_df = suspense_credit(df)
    suspense_debit_df = suspense_debit(df)
    payment_df = payment(df)
    receipt_df = receipt(df)

    bank_avg_balance_df = calculate_fixed_day_average(eod_sheet_df)
    loan_value_df = process_avg_last_6_months(bank_avg_balance_df, eod_sheet_df)

    # Build a dictionary to hold the labeled DataFrames
    result_dict = {
        # "Name Acc No": name_n_num_df.to_dict(orient="records"),
        "Particulars": particulars_df.to_dict(orient="records"),
        "Income Receipts": income_receipts_df.to_dict(orient="records"),
        "Important Expenses": imp_expenses_payments_df.to_dict(orient="records"),
        "Other Expenses": other_expenses_df.to_dict(orient="records"),
        "Opportunity to Earn": loan_value_df.to_dict(orient="records"),
        "Transactions": transaction_sheet_df.to_dict(orient="records"),
        "EOD": eod_sheet_df.to_dict(orient="records"),
        "Investment": investment_df.to_dict(orient="records"),
        "Creditors": creditor_df.to_dict(orient="records"),
        "Debtors": debtor_df.to_dict(orient="records"),
        "UPI-CR": upi_cr_df.to_dict(orient="records"),
        "UPI-DR": upi_dr_df.to_dict(orient="records"),
        "Cash Withdrawal": cash_withdrawal_df.to_dict(orient="records"),
        "Cash Deposit": cash_deposit_df.to_dict(orient="records"),
        "Redemption, Dividend & Interest": dividend_int_df.to_dict(orient="records"),
        "Probable EMI": emi_df.to_dict(orient="records"),
        "Refund-Reversal": refund_df.to_dict(orient="records"),
        "Suspense Credit": suspense_credit_df.to_dict(orient="records"),
        "Suspense Debit": suspense_debit_df.to_dict(orient="records"),
        "Payment Voucher": payment_df.to_dict(orient="records"),
        "Receipt Voucher": receipt_df.to_dict(orient="records"),
    }

    # Convert the entire dictionary to JSON
    json_output = json.dumps(result_dict, indent=4)

    return json_output


def start_extraction_edit_pdf(bank_names, pdf_paths, passwords, start_dates, end_dates, CA_ID, progress_data, explicit_lines_list, whole_transaction_sheet=None):
    account_number = ""
    dfs = {}
    name_dfs = {}
    pdf_paths_not_extracted = {
        "paths": [],
        "passwords": [],
        "start_dates": [],
        "end_dates": [],
        "respective_list_of_columns": []
    }
    i = 0

    for bank in bank_names:
        bank = str(f"{bank}{i}")
        pdf_path = pdf_paths[i]
        pdf_password = passwords[i]
        start_date = start_dates[i]
        end_date = end_dates[i]
        explicit_lines = explicit_lines_list[i]

        dfs[bank], name_dfs[bank] = extraction_process_explicit_lines(bank, pdf_path, pdf_password, start_date, end_date, explicit_lines)

        print(f"Extracted {bank} bank statement successfully")
        # account_number += f"{name_dfs[bank][1][:4]}x{name_dfs[bank][1][-4:]}_"
        # Check if the extracted dataframe is empty
        if dfs[bank].empty:
            pdf_paths_not_extracted["paths"].append(pdf_path)
            pdf_paths_not_extracted["passwords"].append(pdf_password)
            pdf_paths_not_extracted["start_dates"].append(start_date)
            pdf_paths_not_extracted["end_dates"].append(end_date)
            pdf_paths_not_extracted["respective_list_of_columns"].append(name_dfs[bank])
            del dfs[bank]
            del name_dfs[bank]

        i += 1

    print("|------------------------------|")
    print(account_number)
    print("|------------------------------|")

    if not dfs:
        folder_path = "saved_pdf"
        try:
            shutil.rmtree(folder_path)
            print(f"Removed all contents in '{folder_path}'")
        except Exception as e:
            print(f"Failed to remove '{folder_path}': {e}")

        return {"sheets_in_json": None, 'pdf_paths_not_extracted': pdf_paths_not_extracted}

    else:
        data = []
        # num_pairs = len(pd.Series(dfs).to_dict())

        for key, value in name_dfs.items():
            bank_name = key
            acc_name = value[0]
            acc_num = value[1]
            if str(acc_num) == "None":
                masked_acc_num = "None"
            else:
                masked_acc_num = "X" * (len(acc_num) - 4) + acc_num[-4:]
            data.append([masked_acc_num, acc_name, bank_name])
            for item in data:
                item[2] = "".join(
                    character for character in item[2] if character.isalpha()
                )

        name_n_num_df = process_name_n_num_df(data)
        list_of_dataframes = list(dfs.values())

        if whole_transaction_sheet is not None:
            list_of_dataframes.append(transaction_sheet)

        # arrange dfs
        initial_df = pd.concat(sort_dataframes_by_date(list_of_dataframes)).fillna("").reset_index(drop=True)

        df = category_add_ca(initial_df)
        new_tran_df = another_method(df)

        #############################------------------------#######################################

        json_lists_of_df = returns_json_output_of_all_sheets(new_tran_df, name_n_num_df)
        # excel_file_path = reconstruct_dict_from_json_save_to_excel(json_lists_of_df, account_number, CA_ID)
        # print(excel_file_path)

        # output_json = process_excel_to_json(filename)

        folder_path = "saved_pdf"
        try:
            shutil.rmtree(folder_path)
            print(f"Removed all contents in '{folder_path}'")
        except Exception as e:
            print(f"Failed to remove '{folder_path}': {e}")

        return {"sheets_in_json": json_lists_of_df, 'pdf_paths_not_extracted': pdf_paths_not_extracted}


def start_extraction_add_pdf(bank_names, pdf_paths, passwords, start_dates, end_dates, CA_ID, progress_data, whole_transaction_sheet=None):
    account_number = ""
    dfs = {}
    name_dfs = {}
    pdf_paths_not_extracted = {
        "paths": [],
        "passwords": [],
        "start_dates": [],
        "end_dates": [],
        "respective_list_of_columns": []
    }
    i = 0

    for bank in bank_names:
        bank = str(f"{bank}{i}")
        pdf_path = pdf_paths[i]
        pdf_password = passwords[i]
        start_date = start_dates[i]
        end_date = end_dates[i]

        dfs[bank], name_dfs[bank] = extraction_process(bank, pdf_path, pdf_password, start_date, end_date)

        print(f"Extracted {bank} bank statement successfully")
        # account_number += f"{name_dfs[bank][1][:4]}x{name_dfs[bank][1][-4:]}_"
        # Check if the extracted dataframe is empty
        if dfs[bank].empty:
            pdf_paths_not_extracted["paths"].append(pdf_path)
            pdf_paths_not_extracted["passwords"].append(pdf_password)
            pdf_paths_not_extracted["start_dates"].append(start_date)
            pdf_paths_not_extracted["end_dates"].append(end_date)
            pdf_paths_not_extracted["respective_list_of_columns"].append(name_dfs[bank])
            del dfs[bank]
            del name_dfs[bank]

        i += 1

    print("|------------------------------|")
    print(account_number)
    print("|------------------------------|")

    if not dfs:
        folder_path = "saved_pdf"
        try:
            shutil.rmtree(folder_path)
            print(f"Removed all contents in '{folder_path}'")
        except Exception as e:
            print(f"Failed to remove '{folder_path}': {e}")

        return {"sheets_in_json": None, 'pdf_paths_not_extracted': pdf_paths_not_extracted}

    else:
        data = []
        # num_pairs = len(pd.Series(dfs).to_dict())

        for key, value in name_dfs.items():
            bank_name = key
            acc_name = value[0]
            acc_num = value[1]
            if str(acc_num) == "None":
                masked_acc_num = "None"
            else:
                masked_acc_num = "X" * (len(acc_num) - 4) + acc_num[-4:]
            data.append([masked_acc_num, acc_name, bank_name])
            for item in data:
                item[2] = "".join(
                    character for character in item[2] if character.isalpha()
                )

        name_n_num_df = process_name_n_num_df(data)
        list_of_dataframes = list(dfs.values())

        if whole_transaction_sheet is not None:
            list_of_dataframes.append(transaction_sheet)

        # arrange dfs
        initial_df = pd.concat(sort_dataframes_by_date(list_of_dataframes)).fillna("").reset_index(drop=True)

        df = category_add_ca(initial_df)
        new_tran_df = another_method(df)

        #############################------------------------#######################################

        json_lists_of_df = returns_json_output_of_all_sheets(new_tran_df, name_n_num_df)

        # excel_file_path = reconstruct_dict_from_json_save_to_excel(json_lists_of_df, account_number, CA_ID)


        folder_path = "saved_pdf"
        try:
            shutil.rmtree(folder_path)
            print(f"Removed all contents in '{folder_path}'")
        except Exception as e:
            print(f"Failed to remove '{folder_path}': {e}")

        return {"sheets_in_json": json_lists_of_df, 'pdf_paths_not_extracted': pdf_paths_not_extracted}

