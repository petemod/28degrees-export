#!/usr/bin/env python3

from __future__ import print_function
import os
from getpass import getpass
import re
from datetime import datetime
import argparse
import codecs
import time
import random
from collections import namedtuple
from functools import reduce

# from selenium import webdriver
from seleniumwire import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

import json

import db
from dateutil import format_tran_date_for_file, format_tran_date_for_qif, \
    parse_tran_date

random.seed()
LOGIN_URL = 'https://servicecentre.latitudefinancial.com.au/login'
WAIT_DELAY = 5
LOGIN_DELAY = 3

Transaction = namedtuple('Transaction',
                         ['date', 'payer', 'amount', 'memo', 'payee'])
export_path = './export'


def messages(before, after_ok, after_fail):
    def external_decorator(f):
        def wrapped(*args, **kwargs):
            print(before)
            r = f(*args, **kwargs)
            print(after_ok if r else after_fail)
            return r

        return wrapped

    return external_decorator


def get_credentials():
    print('Enter your username:')
    lines = []
    lines.append(input())
    lines.append(getpass())

    return lines


def get_next_btn(browser):
    return browser.find_element(By.NAME, 'nextButton')


def login(creds, captcha):
    driver = webdriver.Chrome()

    driver.get(LOGIN_URL)

    if captcha:
        print('Press enter to continue after Captcha:')
        input()
    else:
        time.sleep(LOGIN_DELAY)

    try:
        user = driver.find_element(By.NAME, 'latitude-id-email-address')
    except NoSuchElementException as exception:
        exit("Could not find the login screen. Use --captcha option if you need to manually complete a captcha")

    user.send_keys(creds[0])
    btn = driver.find_element(By.CSS_SELECTOR, "div[class*='login_container'] div[class*='loginWidget'] button")
    btn.click()
    time.sleep(LOGIN_DELAY)
    user = driver.find_element(By.NAME, 'password')
    user.send_keys(creds[1])
    btn = driver.find_element(By.CSS_SELECTOR, "#loginScrollableContainer button > span")

    # btn = driver.find_element(By.NAME, 'SUBMIT')
    btn.click()

    time.sleep(WAIT_DELAY)

    try:
        terms_link = driver.find_element(By.CSS_SELECTOR, '#loginScrollableContainer > div > div > section > button')
        terms_link.click()
    except Exception as exc:
        pass

    time.sleep(WAIT_DELAY)
    # Find all buttons
    buttons = driver.find_elements(By.TAG_NAME, "button")

    tranLink = None
    for button in buttons:
        if button.text == 'View transactions':
            tranLink = button
            break

    tranLink.click()

    # nextBtn = get_next_btn(driver)

    return driver


def fetch_transactions(driver):
    time.sleep(WAIT_DELAY)

    # load 2nd page if it's available
    try:
        next_tran = driver.find_element(By.XPATH, '//*[@id="transaction-list"]/div[2]/button')
        next_tran.click()
        time.sleep(WAIT_DELAY)
    except Exception as exc:
        pass

    transaction_data = []
    for req in driver.requests:
        if 'transactions' in req.url:
            if req.response.headers.get('Content-Type') == 'application/json':
                transaction_data.append(req.response.body)
    trans = []
    for tran_data in transaction_data:
        tran_json = json.loads(tran_data)
        for tran in tran_json['transactions']:

            date = parse_tran_date(tran['transaction_date'])
            desc_payee = '%s %s' % (tran['merchant']['title'], tran['merchant']['subtitle'])
            amount = tran['amount']
            if tran['type'] != 'CREDIT':
                amount = -amount
            payer = ''

            if len(desc_payee) >= 23:
                payee = desc_payee[:23]
                memo = desc_payee[23:]
            else:
                payee = desc_payee
                memo = ''

            # Clean up the data
            amount = str(amount).replace('$', '')
            payee = re.sub('\s+', ' ', payee)
            memo = re.sub('\s+', ' ', memo)

            trans.append(Transaction(date=date,
                                     payer=payer,
                                     amount=amount,
                                     memo=memo,
                                     payee=payee))

    return trans


"""See http://en.wikipedia.org/wiki/Quicken_Interchange_Format for more info."""


@messages('Writing QIF file...', 'OK', '')
def write_qif(trans, file_name):
    print(file_name)
    with codecs.open(file_name, 'w', encoding='utf-8') as f:
        # Write header
        print('!Account', file=f)
        print('NQIF Account', file=f)
        print('TCCard', file=f)
        print('^', file=f)
        print('!Type:CCard', file=f)

        for t in trans:
            print('C', file=f)  # status - uncleared
            print('D' + format_tran_date_for_qif(t.date), file=f)  # date
            print('T' + t.amount, file=f)  # amount
            print('M' + t.payer, file=f)
            print('P' + t.payee + t.memo, file=f)
            print('^', file=f)  # end of record


@messages('Writing CSV file...', 'OK', '')
def write_csv(trans, file_name):
    print(file_name)
    with codecs.open(file_name, 'w', encoding='utf-8') as f:
        print('Date,Amount,Payer,Payee', file=f)
        for t in trans:
            print('"%s","%s","%s","%s"' % (format_tran_date_for_qif(t.date), t.amount, t.payer, t.payee), file=f)


def get_file_name(export_path, s_d, e_d, extension):
    i = 0
    while True:
        f_n = os.path.join(export_path, '%s-%s%s.%s' %
                           (format_tran_date_for_file(s_d),
                            format_tran_date_for_file(e_d),
                            '' if i == 0 else '-%s' % i,
                            extension))
        if not os.path.exists(f_n):
            return f_n

        i += 1


def export(csv, slow, captcha):
    print('Use "export.py --help" to see all command line options')
    WAIT_DELAY = 5
    LOGIN_DELAY = 3
    if slow:
        WAIT_DELAY = 25

    if not os.path.exists(export_path):
        os.makedirs(export_path)

    t_db = db.init_db()
    if not t_db:
        print('Error initialising database')
        return

    creds = get_credentials()
    driver = login(creds, captcha)

    trans = []

    page_trans = fetch_transactions(driver)
    trans += page_trans

    page_count = len(page_trans)

    print('Got %s transactions, from %s to %s' % (page_count,
                                                  format_tran_date_for_qif(page_trans[0].date),
                                                  format_tran_date_for_qif(page_trans[-1].date)))

    new_trans = db.get_only_new_transactions(trans)
    print('Total of %s new transactions obtained' % len(new_trans))

    if len(new_trans) != 0:

        print('Saving transactions...')
        db.save_transactions(new_trans)

        s_d = reduce(lambda t1, t2: t1 if t1.date < t2.date else t2, new_trans).date
        e_d = reduce(lambda t1, t2: t1 if t1.date > t2.date else t2, new_trans).date

        if csv:
            file_name = get_file_name(export_path, s_d, e_d, 'csv')
            write_csv(new_trans, file_name)
        else:
            file_name = get_file_name(export_path, s_d, e_d, 'qif')
            write_qif(new_trans, file_name)

    """
    if statements:

        if len(statLink) == 0:
            print('Unable to find link to statements page')
            return

        br.open(statLink[0].attrib['href'])
        text = br.response().read()
        q = PyQuery(text)

        for row in q('a[class="s_downloads"]'):
            statement_date = datetime.strptime(row.text, '%d %b %Y').strftime('%Y-%m-%d')
            statement_name = '28 Degrees Statement ' + statement_date + '.pdf'
            statement_path = os.path.join(export_path, statement_name)

            if not os.path.exists(statement_path):
                print('Retrieving statement ' + row.text + ' and saving to ' + statement_path)
                br.retrieve(row.attrib['href'], statement_path)

    """


if __name__ == "__main__":
    parser = argparse.ArgumentParser("""I load transactions from 28degrees-online.latitudefinancial.com.au.
If no arguments specified, I will produce a nice QIF file for you
To get CSV, specify run me with --csv parameter""")
    parser.add_argument('--csv', action='store_true', help='Write CSV instead of QIF')
    parser.add_argument('--slow', action='store_true',
                        help='Increase wait delay between actions. Use on slow internet connections or when 28degrees is acting up.')
    parser.add_argument('--captcha', action='store_true',
                        help='Wait until enter pressed, before login, to allow manual completion of captcha.')
    # parser.add_argument('--statements', action='store_true', default=False)
    args = parser.parse_args()
    export(**vars(args))
