from cryptography.fernet import Fernet
import bcrypt
import json
import logging
import telegram.ext
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler
from telegram import InlineQueryResultArticle, ParseMode, InputTextMessageContent
import random
import requests
import mysql.connector
import string
import hashlib
import re
import time
import getpass

from uuid import uuid4
from telegram.utils.helpers import escape_markdown
from datetime import datetime

mysql_host = 'yourHots'
mysql_port = 330x
mysql_db = 'yourDB'
mysql_user = 'yourUser'
mysql_pass = 'topSecret'

aie_node_api = 'http://localhost:6870/nxt'
aiq_asset_id = '5384720030523531536'

lottery_aie_price = 2
lottery_aiq_price = 10
lottery_aiq_blocks = 100
determine_lottery_block_shift = 3
secure_lottery_block_shift = 10

lottery_account = "LOTTERY"

telegram_token='telegram token goes here'
aie_key=b'some nice secret key to encrypt paswords goes here'

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Common functions
def encrypt_string(hash_string):
    sha_signature = hashlib.sha256(hash_string.encode()).hexdigest()
    return str(sha_signature)

def randomString():
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ' '.join(''.join(random.choice(letters) for i in range(random.randint(6,10))) for i in range(12))

def get_explorer_transaction_url(transactionID):
    return 'https://block.hebeblock.com/#/transaction/'+str(transactionID)+'?type=Aie'

def update_usertelegram(user):
    conn = mysql.connector.connect(host=mysql_host,user=mysql_user,password=mysql_pass,database=mysql_db)
    c = conn.cursor()
    cmd = "INSERT IGNORE INTO usertelegram (name) VALUES (%s)"
    c.execute(cmd, (user, ))
    conn.commit()
    conn.close()

def check_coingecko():
    api_url = requests.get('https://api.coingecko.com/api/v3/coins/artiqox?localization=false')
    market_data_json = api_url.json()
    current_price_json = json.loads(json.dumps(market_data_json['market_data']))
    currency_json = json.loads(json.dumps(current_price_json['current_price']))
    return currency_json

def check_frei():
    api_url = requests.get('https://api.freiexchange.com/public/ticker/AIE')
    market_data_json = api_url.json()
    current_price_json = json.loads(json.dumps(market_data_json['AIE_BTC']))
    currency_json = json.loads(json.dumps(current_price_json[0]))
    return currency_json

def get_aiq_secret(aie_secret_encrypted, aie_salt):
    f = Fernet(aie_key)
    aie_secret = f.decrypt(aie_secret_encrypted.encode()).decode().replace(' '+aie_salt,'')
    return aie_secret

def get_aiq_account(giveaiq_user_name):
    conn = mysql.connector.connect(host=mysql_host,user=mysql_user,password=mysql_pass,database=mysql_db)
    c = conn.cursor()
    cmd = "select count(*) from user where username = %s"
    aie_account_cursor = c.execute(cmd, (giveaiq_user_name, ))
    rows = c.fetchone()
    aie_account_exists = int(rows[0])
    if aie_account_exists == 0:
        aie_salt = bcrypt.gensalt().decode("utf-8")
        password_hash = bcrypt.gensalt().decode("utf-8")
        aie_secret = randomString()
        aie_secret_obfuscate = aie_secret + ' ' + aie_salt
        aiereponse = requests.post(aie_node_api+'?requestType=getAccountId', data={'secretPhrase':aie_secret})
        json_aieresponse = aiereponse.json()
        aie_account = json_aieresponse["accountRS"]
        aie_public_key = json_aieresponse["publicKey"]
        f = Fernet(aie_key)
        aie_secret_encrypted = f.encrypt(aie_secret_obfuscate.encode())
        cmd = "INSERT INTO user (username, displayname, password_hash, aie_account, aie_public_key, aie_secret_encrypted, aie_salt) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        c.execute(cmd, (giveaiq_user_name, giveaiq_user_name[3:], password_hash, aie_account, aie_public_key, aie_secret_encrypted, aie_salt))
        conn.commit()
        update_usertelegram(giveaiq_user_name[3:])
    else:
        cmd = "select aie_account, aie_public_key, aie_secret_encrypted, aie_salt from user where username = (%s)"
        aie_account_cursor = c.execute(cmd, (giveaiq_user_name, ))
        rows = c.fetchone()
        aie_account = rows[0]
        aie_public_key = rows[1]
        aie_secret_encrypted = rows[2]
        aie_salt = rows[3]
        aie_secret = get_aiq_secret(aie_secret_encrypted, aie_salt)
    conn.close()
    return aie_account, aie_public_key, aie_secret

def get_aiq_balance(aie_account):
    aiereponse = requests.post(aie_node_api+'?requestType=getAccountAssets', data={'account':aie_account, 'asset':aiq_asset_id})
    json_aieresponse = aiereponse.json()
    try:
        balance = float(json_aieresponse["quantityQNT"])/100
    except Exception as e:
        balance = 0.0
    return balance

def get_aie_balance(aie_account):
    aiereponse = requests.post(aie_node_api+'?requestType=getBalance', data={'account':aie_account})
    json_aieresponse = aiereponse.json()
    try:
        balance = float(json_aieresponse["balanceNQT"])/100000000
    except Exception as e:
        balance = 0.0
    return balance

def telegram_giver(giveaiq_user_name, giveaiq_user_name_target, aie_account, aie_account_target, amount_aiq, aie_public_key, aie_secret, aie_public_key_target, in_reply_to_status_id_str, coin, giver_type, message):
    giveaiq_displayname = giveaiq_user_name[3:]
    giveaiq_accounttype = giveaiq_user_name[0:3]
    giveaiq_displayname_target = giveaiq_user_name_target[3:]
    giveaiq_accounttype_target = giveaiq_user_name_target[0:3]
    json_aieresponse = 'Empty'
    if coin == "aiq" and giver_type == "give":
        balance_converted = str(amount_aiq*100)
        conn = mysql.connector.connect(host=mysql_host,user=mysql_user,password=mysql_pass,database=mysql_db)
        c = conn.cursor()
        if in_reply_to_status_id_str:
            aiereponse = requests.post(aie_node_api+'?requestType=transferAsset', data={'recipient':aie_account_target, 'asset':aiq_asset_id, 'quantityQNT':balance_converted.split(".")[0], 'feeNQT':100000000, 'publicKey':aie_public_key, 'secretPhrase':aie_secret, 'deadline':1440, 'recipientPublicKey':aie_public_key_target})
            json_aieresponse = aiereponse.json()
            try:
                transactionID = json.loads(json.dumps(json_aieresponse['transaction']))
            except Exception as e:
                transactionID = 0

            amount_aiq = '{0:.2f}'.format(float(amount_aiq))
            cmd = "UPDATE twitter_tweet SET total_received_amount = total_received_amount + %s, total_received_number = total_received_number + 1 WHERE id=%s"
            c.execute(cmd, (amount_aiq, in_reply_to_status_id_str, ))
            cmd = "UPDATE usertwitter SET total_received_amount = total_received_amount + %s, total_received_number = total_received_number + 1 WHERE screen_name=%s"
            c.execute(cmd, (amount_aiq, giveaiq_displayname_target, ))
            cmd = "UPDATE usertelegram SET total_gives_amount = total_gives_amount + %s, total_gives_number = total_gives_number + 1 WHERE screen_name=%s"
            c.execute(cmd, (amount_aiq, giveaiq_displayname, ))
            conn.commit()
        else:
            aiereponse = requests.post(aie_node_api+'?requestType=transferAsset', data={'recipient':aie_account_target, 'asset':aiq_asset_id, 'quantityQNT':balance_converted.split(".")[0], 'feeNQT':100000000, 'publicKey':aie_public_key, 'secretPhrase':aie_secret, 'deadline':1440, 'recipientPublicKey':aie_public_key_target})
            json_aieresponse = aiereponse.json()
            try:
                transactionID = json.loads(json.dumps(json_aieresponse['transaction']))
            except Exception as e:
                transactionID = 0
            if giveaiq_accounttype_target == "TG-":
                cmd = "UPDATE usertelegram SET total_received_amount = total_received_amount + %s, total_received_number = total_received_number + 1 WHERE name=%s"
            elif giveaiq_accounttype_target == "TW-":
                cmd = "UPDATE usertwitter SET total_received_amount = total_received_amount + %s, total_received_number = total_received_number + 1 WHERE screen_name=%s"
            c.execute(cmd, (amount_aiq, giveaiq_displayname_target, ))
            cmd = "UPDATE usertelegram SET total_gives_amount = total_gives_amount + %s, total_gives_number = total_gives_number + 1 WHERE name=%s"
            c.execute(cmd, (amount_aiq, giveaiq_displayname, ))
            conn.commit()
        conn.close()
    elif coin == "aie" and giver_type == "give":
        balance_converted = str(amount_aiq*100000000)
        if in_reply_to_status_id_str:
            aiereponse = requests.post(aie_node_api+'?requestType=sendMoney', data={'recipient':aie_account_target, 'amountNQT':balance_converted.split(".")[0], 'feeNQT':100000000, 'publicKey':aie_public_key, 'secretPhrase':aie_secret, 'deadline':1440, 'recipientPublicKey':aie_public_key_target})
            json_aieresponse = aiereponse.json()
            try:
                transactionID = json.loads(json.dumps(json_aieresponse['transaction']))
            except Exception as e:
                transactionID = 0
        else:
            aiereponse = requests.post(aie_node_api+'?requestType=sendMoney', data={'recipient':aie_account_target, 'amountNQT':balance_converted.split(".")[0], 'feeNQT':100000000, 'publicKey':aie_public_key, 'secretPhrase':aie_secret, 'deadline':1440, 'recipientPublicKey':aie_public_key_target})
            json_aieresponse = aiereponse.json()
            try:
                transactionID = json.loads(json.dumps(json_aieresponse['transaction']))
                
            except Exception as e:
                transactionID = 0

    elif coin == "aiq" and giver_type == "lottery":
        balance_converted = str(amount_aiq*100)
        aiereponse = requests.post(aie_node_api+'?requestType=transferAsset', data={'recipient':aie_account_target, 'asset':aiq_asset_id, 'quantityQNT':balance_converted.split(".")[0], 'feeNQT':200000000, 'messageIsPrunable':'false', 'message':message, 'messageIsText':'true', 'publicKey':aie_public_key, 'secretPhrase':aie_secret, 'deadline':1440, 'recipientPublicKey':aie_public_key_target})
        json_aieresponse = aiereponse.json()
        try:
            transactionID = json.loads(json.dumps(json_aieresponse['transaction']))
        
        except Exception as e:
            transactionID = 0

    return transactionID, json_aieresponse

def getBlockchainHeight():
    try:
        aiereponse = requests.post(aie_node_api+'?requestType=getBlockchainStatus')
        json_aieresponse = aiereponse.json()
        try:
            blockchainHeight = int(json_aieresponse["numberOfBlocks"])
        except Exception as e:
            blockchainHeight = 0
    except Exception as e:
        blockchainHeight = 0
    return(blockchainHeight)

# handlers

def lotteryMe(update, context):

    user = update.message.from_user.username
    
    if user is None:
        update.message.reply_text("Please set a telegram username in your profile settings!")
    else:
        giveaiq_user_name = "TG-"+user
        pattern = re.compile(r'^/gameMyDude\s{1}@(\w+)', re.IGNORECASE)
        result = pattern.match(update.message.text)
        if result:
            target_giveaiq_user_name = "TG-"+result.group(1)
        else:
            target_giveaiq_user_name = giveaiq_user_name
        amount = lottery_aiq_price
        aie_account, aie_public_key, aie_secret = get_aiq_account(giveaiq_user_name)
        balance = get_aiq_balance(aie_account)
        balance_aie = get_aie_balance(aie_account)
        if balance < amount:
            update.message.reply_text("@{0} you have insufficent AIQ funds.".format(user))
        elif balance_aie < lottery_aie_price:
            update.message.reply_text("@{0} you have insufficent AIE funds, deposit some now or make sure you have AIQ on this account then wait for hodlers rewards.".format(user))
        else:
            aie_lottery_account, aie_lottery_public_key, aie_lottery_secret = get_aiq_account(lottery_account)
            amount_converted = str(amount*100)
            blockchainHeight = getBlockchainHeight()
            ongoing_lottery = ''.join(str(blockchainHeight).split())
            
            if int(ongoing_lottery[-2:]) >= 98:
                ongoing_lottery_draw_aprox_block = str(((int(ongoing_lottery[:-2])+2)*lottery_aiq_blocks)+10)
                ongoing_lottery_draw_aprox_minutes = str((((int(ongoing_lottery[:-2])+2)*lottery_aiq_blocks)+10)-blockchainHeight)
                ongoing_lottery = str(int(ongoing_lottery[:-2])+1)
            else:
                ongoing_lottery_draw_aprox_block = str(((int(ongoing_lottery[:-2])+1)*lottery_aiq_blocks)+10)
                ongoing_lottery_draw_aprox_minutes = str((((int(ongoing_lottery[:-2])+1)*lottery_aiq_blocks)+10)-blockchainHeight)
                ongoing_lottery = ongoing_lottery[:-2]
                
            aiereponse = requests.post(aie_node_api+'?requestType=transferAsset', data={'recipient':aie_lottery_account, 'asset':aiq_asset_id, 'quantityQNT':amount_converted.split(".")[0], 'feeNQT':200000000, 'messageIsPrunable':'false', 'message':'#GameOfTransactions '+ongoing_lottery+' '+target_giveaiq_user_name, 'messageIsText':'true', 'publicKey':aie_public_key, 'secretPhrase':aie_secret, 'deadline':1440})
            json_aieresponse = aiereponse.json()
            
            try:
                transactionID = json.loads(json.dumps(json_aieresponse['transaction']))
                if target_giveaiq_user_name == giveaiq_user_name:
                    update.message.reply_text("@{0} Preparing Game of Transactions # {3} seat, check <a href=\"{5}\">status</a>. Draw after block {4}, approx in {6} minutes".format(user,amount,lottery_aie_price,ongoing_lottery,ongoing_lottery_draw_aprox_block,get_explorer_transaction_url(transactionID),ongoing_lottery_draw_aprox_minutes),parse_mode=ParseMode.HTML)
                else:
                    update.message.reply_text("@{7} your friend @{0} is setting you up for Game of Transactions # {3}, check <a href=\"{5}\">status</a>. Draw after block {4}, approx in {6} minutes".format(user,amount,lottery_aie_price,ongoing_lottery,ongoing_lottery_draw_aprox_block,get_explorer_transaction_url(transactionID),ongoing_lottery_draw_aprox_minutes,target_giveaiq_user_name[3:]),parse_mode=ParseMode.HTML)
            except Exception as e:
                transactionID = 0
                update.message.reply_text("Something went wrong, "+str(json_aieresponse))

aie_lottery_account, aie_lottery_public_key, aie_lottery_secret = get_aiq_account(lottery_account)
aiereponse = requests.post(aie_node_api+'?requestType=getAccountLedger', data={'account':aie_lottery_account,'lastIndex':0,'eventType':'ASSET_TRANSFER','holding':aiq_asset_id,'includeTransactions':'true'})
json_aieresponse = aiereponse.json()
try:
    lastLotteryPaid_string = json_aieresponse['entries'][0]['transaction']['attachment']['message']
    pattern = re.compile(r'^Winner of #GameOfTransactions\s{1}(\d+)\s{1}(TG|TW)\-(\w+)$')
    result = pattern.match(lastLotteryPaid_string)
    if result:
        lastLotteryPaid = result.group(1)
    else:
        lastLotteryPaid = 0
    lastLotteryPaid_height = json_aieresponse['entries'][0]['height']
    lastLotteryPaid_transaction = json_aieresponse['entries'][0]['transaction']['transaction']
except Exception as e:
    lastLotteryPaid = 0
    lastLotteryPaid_height = 0

running_flag = {'status': 0, 'lastPaidHeight': lastLotteryPaid_height}
processed_lottery = {lastLotteryPaid: {}}
processed_lottery.setdefault(lastLotteryPaid, {})["transactionID"] = lastLotteryPaid_transaction
processed_lottery.setdefault(lastLotteryPaid, {})["announced"] = "yes"

def lottery(context: telegram.ext.CallbackContext):
    if running_flag.get("status") == 0:
        running_flag['status'] = 1
        blockchainHeight = getBlockchainHeight()

        ongoing_lottery = ''.join(str(blockchainHeight).split())
        
        if int(ongoing_lottery[-2:]) >= 98:
            ongoing_lottery_draw_aprox_block = str(((int(ongoing_lottery[:-2])+2)*lottery_aiq_blocks)+10)
            ongoing_lottery_draw_aprox_minutes = str((((int(ongoing_lottery[:-2])+2)*lottery_aiq_blocks)+10)-blockchainHeight)
            ongoing_lottery = str(int(ongoing_lottery[:-2])+1)
            previous_lottery = int(ongoing_lottery)-2
        else:
            ongoing_lottery_draw_aprox_block = str(((int(ongoing_lottery[:-2])+1)*lottery_aiq_blocks)+10)
            ongoing_lottery_draw_aprox_minutes = str((((int(ongoing_lottery[:-2])+1)*lottery_aiq_blocks)+10)-blockchainHeight)
            ongoing_lottery = ongoing_lottery[:-2]
            previous_lottery = int(ongoing_lottery)-1
        
        required_previous_lottery_block = (previous_lottery*lottery_aiq_blocks)+lottery_aiq_blocks
        if processed_lottery.get(previous_lottery, 0) == 0 and blockchainHeight >= required_previous_lottery_block+secure_lottery_block_shift:
            aie_lottery_account, aie_lottery_public_key, aie_lottery_secret = get_aiq_account(lottery_account)
            processed_lottery.setdefault(previous_lottery, {})["status"] = "processing"

            aiereponse = requests.post(aie_node_api+'?requestType=getBlocks', data={'firstIndex':0, 'lastIndex':(blockchainHeight-previous_lottery*lottery_aiq_blocks)+lottery_aiq_blocks})
            json_aieresponse = aiereponse.json()
            
            aie_blocks = json.loads(json.dumps(json_aieresponse['blocks']))
            list_of_coupons = []

            for block in aie_blocks:
                #conditions of last lottery block and last+determine_lottery_block_shift blocks are used to determine the winner
                if block['height'] == required_previous_lottery_block+determine_lottery_block_shift:
                    determine_lottery_timestamp = block['timestamp']

                if block['height'] == required_previous_lottery_block:
                    determine_lottery_transactions = len(block['transactions'])
                    
                for transactionID in block['transactions']:
                    aiereponse = requests.post(aie_node_api+'?requestType=getTransaction', data={'transaction':transactionID})
                    json_aieresponse = aiereponse.json()
                    aie_transaction_type = json.loads(json.dumps(json_aieresponse['type']))
                    aie_transaction_subtype = json.loads(json.dumps(json_aieresponse['subtype']))
                    try:
                        aie_transaction_recepient = json.loads(json.dumps(json_aieresponse['recipientRS']))
                    except Exception as e:
                        aie_transaction_recepient = 0
                    aie_transaction_sender = json.loads(json.dumps(json_aieresponse['senderRS']))
                    aie_transaction_confirmations = json.loads(json.dumps(json_aieresponse['confirmations']))
                    try:
                        aie_transaction_asset = json.loads(json.dumps(json_aieresponse['attachment']['asset']))
                    except Exception as e:
                        aie_transaction_asset = 0
                    try:
                        aie_transaction_amount = json.loads(json.dumps(json_aieresponse['attachment']['quantityQNT']))
                    except Exception as e:
                        aie_transaction_amount = 0
                    try:
                        aie_transaction_message = json.loads(json.dumps(json_aieresponse['attachment']['message']))
                    except Exception as e:
                        aie_transaction_message = "notAlottery"
                    pattern = re.compile(r'^(#GameOfTransactions|Winner of #GameOfTransactions)\s{1}(\d+)\s{1}(TG|TW)\-(\w+)$')
                    result = pattern.match(aie_transaction_message)
                    if result:
                        if aie_transaction_type == 2 and aie_transaction_subtype == 1 and aie_transaction_asset == aiq_asset_id and aie_transaction_recepient == aie_lottery_account and result.group(2) == str(previous_lottery) and result.group(1) == "#GameOfTransactions" and int(aie_transaction_amount) == lottery_aiq_price*100 and int(aie_transaction_confirmations) > 1 and block['height'] <= required_previous_lottery_block:
                            list_of_coupons.append(result.group(3)+'-'+result.group(4))
                            
                        elif aie_transaction_type == 2 and aie_transaction_subtype == 1 and aie_transaction_asset == aiq_asset_id and aie_transaction_sender == aie_lottery_account and result.group(2) == str(previous_lottery) and result.group(1) == "Winner of #GameOfTransactions":
                            processed_lottery.setdefault(previous_lottery, {})["transactionID"] = transactionID
                            processed_lottery.setdefault(previous_lottery, {})["winner"] = result.group(3)+'-'+result.group(4)
                            processed_lottery.setdefault(previous_lottery, {})["amount_aiq"] = int(aie_transaction_amount)/100
                            processed_lottery.setdefault(previous_lottery, {})["announced"] = "yes"
                        processed_lottery.setdefault(previous_lottery, {})["list_of_coupons"] = list_of_coupons

            if len(list_of_coupons) >=1:
                if len(list_of_coupons) == 1:
                    lottery_winner = list_of_coupons[0]
                else:
                    winning_coupon_position = (determine_lottery_timestamp+determine_lottery_transactions) % len(list_of_coupons)
                    lottery_winner = list_of_coupons[winning_coupon_position]
                print('test run from algo winner is {}'.format(lottery_winner))

            if processed_lottery.get(previous_lottery).get('transactionID', "notYet") == "notYet":
                if len(list_of_coupons) >=1:
                    if len(list_of_coupons) == 1:
                        lottery_winner = list_of_coupons[0]
                    else:
                        winning_coupon_position = (determine_lottery_timestamp+determine_lottery_transactions) % len(list_of_coupons)
                        lottery_winner = list_of_coupons[winning_coupon_position]
                    processed_lottery.setdefault(previous_lottery, {})["winner"] = lottery_winner
                    aie_account_target, aie_public_key_target, aie_secret_target = get_aiq_account(lottery_winner)
                    amount_aiq = (len(list_of_coupons)*lottery_aiq_price)-2
                    processed_lottery.setdefault(previous_lottery, {})["amount_aiq"] = amount_aiq
                    transactionID, json_response = telegram_giver(lottery_account, lottery_winner, aie_lottery_account, aie_account_target, amount_aiq, aie_lottery_public_key, aie_lottery_secret, aie_public_key_target, "", "aiq", "lottery", "Winner of #GameOfTransactions "+str(previous_lottery)+" "+lottery_winner)
                    processed_lottery.setdefault(previous_lottery, {})["list_of_coupons"] = list_of_coupons
                    if str(transactionID) == "0":
                        processed_lottery.setdefault(previous_lottery, {})["transactionID"] = json_response
                    else:
                        processed_lottery.setdefault(previous_lottery, {})["transactionID"] = transactionID
                else:
                    lottery_winner = "No Participants"
                    processed_lottery.setdefault(previous_lottery, {})["transactionID"] = "No Participants"
                    processed_lottery.setdefault(previous_lottery, {})["winner"] = "No Participants"
                    processed_lottery.setdefault(previous_lottery, {})["list_of_coupons"] = "No Participants"
                    processed_lottery.setdefault(previous_lottery, {})["amount_aiq"] = 0
                processed_lottery.setdefault(previous_lottery, {})["blockchainHeight"] = blockchainHeight

            if processed_lottery.get(previous_lottery).get('transactionID', "0") != "0":
                lottery_winner = processed_lottery.get(previous_lottery).get('winner', "0")
                amount_aiq = processed_lottery.get(previous_lottery).get('amount_aiq', 0)
                processed_lottery.setdefault(previous_lottery, {})["status"] = "done"
                if lottery_winner[0:3] == "TG-" and processed_lottery.get(previous_lottery).get('announced', "no") != "yes":
                    context.bot.send_message(chat_id='@Artiqox', text="It is my pleasure to announce that telegram user @{0} won #GameOfTransactions # {1}, {2} of AIQ has been transfered to the winner, transaction <a href=\"{3}\">details</a>. Congrats.".format(lottery_winner[3:],str(previous_lottery),str(amount_aiq),get_explorer_transaction_url(transactionID)),parse_mode=ParseMode.HTML)
                elif lottery_winner[0:3] == "TW-" and processed_lottery.get(previous_lottery).get('announced', "no") != "yes":
                    context.bot.send_message(chat_id='@Artiqox', text="It is my pleasure to announce that twitter user @{0} won #GameOfTransactions # {1}, {2} of AIQ has been transfered to the winner, transaction <a href=\"{3}\">details</a>. Congrats.".format(lottery_winner[3:],str(previous_lottery),str(amount_aiq),get_explorer_transaction_url(transactionID)),parse_mode=ParseMode.HTML)
                print('lottery {}'.format(str(previous_lottery)))

                print(lottery_winner)
                print(lottery_winner[0:2])
                processed_lottery.setdefault(previous_lottery, {})["announced"] = "yes"
                print(processed_lottery.get(previous_lottery))

        running_flag['status'] = 0

    else:
        print("Previous run still on going... skipping")

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(telegram_token, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("gameMe", lotteryMe))
    dp.add_handler(CommandHandler("gameMyDude", lotteryMe))

    # add scheduled jobs
    j = updater.job_queue
    job_lottery = j.run_repeating(lottery, interval=60, first=0)
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
