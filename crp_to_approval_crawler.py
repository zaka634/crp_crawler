import collections
import csv
import datetime
import json
import re
import time
from datetime import timedelta

import requests
import gspread
from bs4 import BeautifulSoup

# instruction to write data to google sheet :
# https://medium.com/analytics-vidhya/how-to-read-and-write-data-to-google-spreadsheet-using-python-ebf54d51a72c

GOOGLE_AUTH_KEY = {
fill in content here
}

DIR_PREFIX = '/home/user/data'


def is_crp(case_number):
    res = requests.get(
        f"https://www.casestatusext.com/cases/{case_number}",
        headers={'User-Agent': 'Custom'},
    )
    soup = BeautifulSoup(res.content, "html.parser")

    crp_section = soup.select("ul.ant-timeline.ant-timeline-label.css-1ij74fp")[0]
    for content in crp_section.contents:
        if "Case Remains Pending" in content.text:
            return True, content.contents[0].text

    return False, ''


def get_case_numbers():
    res = requests.get(
        "https://www.casestatusext.com/approvals/I-485/MSC-LB",
        headers={'User-Agent': 'Custom'},
    )
    soup = BeautifulSoup(res.content, "html.parser")
    section = soup.findAll("script")[-1]
    x = section.string.strip()
    x = x[26:-5]
    x = re.sub(r"[\n\t\s]*", "", x)  # Removing the newlines, spaces and tabs from string
    x = re.sub(r"\\", "", x)  # Removing the newlines, spaces and tabs from string
    x = json.loads(x)
    case_by_day_list = x[0][3]['data']['all']

    result = collections.defaultdict(list)
    for cc_by_day in case_by_day_list:
        result[cc_by_day['d']] = sorted([x['cid'] for x in cc_by_day["cases"]])

    return result


def check_crp_status(case_numbers, processed_file_path, query_date, processed_cases=None):
    if processed_cases is None:
        processed_cases = set()

    start_time = time.time()
    print(f"start time: {start_time}")
    crp_list = []
    error_list = []

    with open(processed_file_path, "a") as processed_file:
        for cc_number in case_numbers:
            if cc_number in processed_cases:
                continue

            time.sleep(1)
            processed_file.write(f'{cc_number}\n')
            # print(f"current processing :{cc_number}")
            try:
                crp, crp_date = is_crp(cc_number)
                if crp:
                    print(f"crp: {cc_number}, crp_date: {crp_date}")
                    crp_list.append([cc_number, query_date, crp_date])
            except Exception as e:
                print(str(e))
                print(f"skip case_number : {cc_number}")
                error_list.append(cc_number)
                continue

    crp_list.sort()

    with open(f'{DIR_PREFIX}/crp_{query_date}.csv', 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(crp_list)
        file.flush()

    if crp_list:
        upload_data_to_google_sheet(crp_list)

    print(f"{query_date}: {len(crp_list)} case approved: {crp_list}")
    print(f"{query_date}: {len(error_list)} case skipped: {error_list}")


def upload_data_to_google_sheet(crp_rows):
    gc = gspread.service_account_from_dict(GOOGLE_AUTH_KEY)
    spreadsheet = gc.open('crp_hell_to_approval')
    worksheet = spreadsheet.worksheet('raw_data')
    worksheet.append_rows(crp_rows)
    print("Data appended successfully.")


def get_7_days(query_date):
    seven_days = [query_date.strftime('%Y-%m-%d')]

    # Loop to get dates for the past 7 days
    for i in range(1, 7):
        past_date = (query_date - timedelta(days=i)).strftime('%Y-%m-%d')
        seven_days.append(past_date)

    return seven_days


def check_crp(query_date, query_day_case_numbers):
    print(f'processing {query_date}')
    processed_case = set()
    try:
        processed_file_path = f'{DIR_PREFIX}/{query_date}'
        with open(processed_file_path, 'r') as f:
            processed_case = set([ln for ln in f.read().splitlines()])
    except FileNotFoundError:
        print(f'{processed_file_path} file does not exist')

    check_crp_status(query_day_case_numbers, processed_file_path, query_date, processed_case)


case_by_day = get_case_numbers()
today = datetime.date.today()
query_days = sorted(get_7_days(today))
for d in query_days:
    current_day_case_numbers = case_by_day[d]
    check_crp(d, current_day_case_numbers)
