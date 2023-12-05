# handle_year, handle_month, handle_day, save_date
# functions for constructing date based on user button interaction

import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime, timedelta, timezone
from collections import defaultdict

TOKEN = 'BOT_TOKEN'
FIREBASE_CREDS_PATH = 'json_file_here'

# Initialize Firebase
cred = credentials.Certificate(FIREBASE_CREDS_PATH)
firebase_app = initialize_app(cred)
db = firestore.client()

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome to ScheduleBot!\n"
                                      "Use /schedule to create your event")

@bot.message_handler(commands=['schedule'])
def schedule(message):
    user_id = message.chat.id
    bot.send_message(user_id, "Write name of your event.")

    bot.register_next_step_handler(message, handle_year)

    # Set the state to 'schedule_handle'
    # bot.register_next_step_handler(message, schedule_handle)


def handle_year(message):
    user_id = message.chat.id
    action_name = message.text

    yearMarkup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    yearMarkup.add(KeyboardButton('2023'))
    yearMarkup.add(KeyboardButton('2024'))
    bot.send_message(user_id, "Choose year of event!", reply_markup=yearMarkup)

    bot.register_next_step_handler(message, handle_month, action_name)

def handle_month(message, action_name):
    user_id = message.chat.id
    year = message.text

    monthMarkup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for month in range(1, 13):
        monthMarkup.add(KeyboardButton(f"{month}"))

    bot.send_message(user_id, "Choose month of event!", reply_markup=monthMarkup)

    bot.register_next_step_handler(message, handle_day, action_name, year)

def handle_day(message, action_name, year):
    user_id = message.chat.id
    month = message.text

    dayMarkup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for day in range(1, 32):
        dayMarkup.add(KeyboardButton(f"{day}"))

    bot.send_message(user_id, "Choose day of the event!", reply_markup=dayMarkup)

    bot.register_next_step_handler(message, save_date,action_name, year, month)

def save_date(message, action_name, year, month):
    user_id = message.chat.id
    day = message.text

    full_date = year + '-' + month + '-' + day
    bot.send_message(user_id, "Write time of your event, for example: 17:56")

    bot.register_next_step_handler(message, schedule_handle, full_date, action_name)


def schedule_handle(message, full_date, action_name):
    user_id = message.chat.id

    try:
        action_name = action_name
        date_str = full_date
        time_str = message.text

        #Create menu
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton('10 min'))
        markup.add(KeyboardButton('15 min'))
        markup.add(KeyboardButton('30 min'))
        markup.add(KeyboardButton('40 min'))

        bot.send_message(user_id, "Choose notification time:", reply_markup=markup)
        bot.register_next_step_handler(message, paste_to_db, action_name, date_str, time_str)
    except Exception as e:
        print(e)
        bot.send_message(user_id, "Something went wrong! Try again.")


def paste_to_db(message, action_name, date_str, time_str):
    user_id = message.chat.id

    try:
        # Parse notification time
        notification_minutes_before = int(message.text.split()[0])

        schedule_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        # Save to Firestore
        doc_ref = db.collection('users').document(str(user_id)).collection('schedules').add({
            'action_name': action_name,
            'schedule_datetime': schedule_datetime,
            'notify_minutes_before': notification_minutes_before
        })

        bot.send_message(user_id, "Your schedule has been saved!")
    except Exception as e:
        print(e)
        bot.send_message(user_id, "Something went wrong! Try again.")


@bot.message_handler(commands=['getschedule'])
def getschedule(message):
    user_id = message.chat.id

    try:
        schedules = db.collection('users').document(str(user_id)).collection('schedules').stream()

        if schedules:
            user_schedule = defaultdict(list)

            for schedule in schedules:
                action_name = schedule.get('action_name')
                schedule_datetime = schedule.get('schedule_datetime')
                notify_minutes_before = schedule.get('notify_minutes_before')

                # Organize data by day
                formatted_date = schedule_datetime.strftime("%Y-%m-%d")
                user_schedule[formatted_date].append({
                    'action_name': action_name,
                    'schedule_datetime': schedule_datetime.strftime("%H:%M"),
                    'notify_minutes_before': notify_minutes_before
                })

            # Create a message with organized schedule
            schedule_text = "Your schedule:\n"
            for date, events in user_schedule.items():
                schedule_text += f"\n{date}:\n"
                for event in events:
                    action_name = event['action_name']
                    schedule_datetime = event['schedule_datetime']
                    notify_minutes_before = event['notify_minutes_before']

                    schedule_text += f"- {action_name} at {schedule_datetime} (with bot notifying {notify_minutes_before} min before event)\n"

            bot.send_message(user_id, schedule_text)
        else:
            bot.reply_to(message, "You haven't scheduled any events yet!")
    except Exception as e:
        print(f"Error handler: {e}")
        bot.send_message(user_id, "Something went wrong!")


@bot.message_handler(func=lambda message: True)
def check_notifications(message):
    now = datetime.now(timezone.utc)
    user_id = message.chat.id

    schedules = db.collection('users').document(str(user_id)).collection('schedules').stream()

    for schedule in schedules:
        schedule_datetime = schedule.get('schedule_datetime')
        notify_minutes_before = schedule.get('notify_minutes_before')

        # Check if it's time to send a notification
        if schedule_datetime - timedelta(minutes=notify_minutes_before) <= now < schedule_datetime:
            bot.send_message(user_id, f"Reminder: {schedule.get('action_name')} is happening in {notify_minutes_before} minutes!")


@bot.message_handler(commands=['makevoicenotice'])
def makevoicenotice(message):
    user_id = message.chat.id
    bot.send_message(user_id, "You can start to record your voice right now!")

    bot.register_next_step_handler(message, voice_handler)

def voice_handler(message):
    user_id = message.chat.id

    try:
        voice = message.voice
        if voice:
            voice_file_id = voice.file_id
            voice_duration = voice.duration

            doc_ref = db.collection('users').document(str(user_id)).collection('voices').add({
                'file_id': voice_file_id,
                'duration': voice_duration,
                'timestamp': datetime.now()
            })

            bot.send_message(user_id, "Your voice notice has been saved!")
        else:
            bot.send_message(user_id, "Probably you dont record your voice. Try again!")
    except Exception as e:
        print(f"Caught: {e}")
        bot.send_message(user_id, "Something went wrong!")


@bot.message_handler(commands=['getvoice'])
def getvoice(message):
    user_id = message.chat.id

    try:
        voices = db.collection('users').document(str(user_id)).collection('voices').stream()

        if voices:
            for voice in voices:
                voice_file_id = voice.get('file_id')
                voice_duration = voice.get('duration')
                timestamp = voice.get('timestamp')

                voice_file_info = bot.get_file(voice_file_id)

                bot.send_voice(user_id, voice_file_info.file_id, caption=f"Duration: {voice_duration}\n"
                                                                         f"Recordered: {timestamp}")
        else:
            bot.send_message(user_id, "There ain't any voice records in you folder!\n"
                                      "Use /makevoicenotice to create one")
    except Exception as e:
        print(f"Caught: {e}")
        bot.send_message(user_id, "Something went wrong")



# Callback inline handle
# @bot.callback_query_handler(func=lambda call: True)
# def handle_callback_query(call: CallbackQuery):
#     user_id = call.from_user.id
#     data = call.data
#
#     bot.answer_callback_query(call.id, text=f"Selected: {data}")
#
#     # Check if the selected data corresponds to a month
#     if data.isdigit() and 1 <= int(data) <= 12:
#         handle_month_callback(call.message, user_id, int(data))
#     # Check if the selected data corresponds to a day
#     elif '1' <= data <= '31':
#         handle_day_callback(call.message, user_id, int(data))
#     elif data.isdigit() and 2023 <= int(data) <= 2024:
#         handle_year_callback(call.message, user_id, int(data))
#     else:
#         bot.send_message(user_id, "Invalid selection. Please try again.")
#
#
# def handle_month_callback(message, user_id, selected_month):
#     # Handle the selected month here
#     bot.send_message(user_id, f"Selected month: {selected_month}")
#
#     bot.register_next_step_handler(message, handle_day)
#
#
# def handle_day_callback(message, user_id, selected_day):
#     # Handle the selected day here
#     bot.send_message(user_id, f"Selected day: {selected_day}")
#
#
# def handle_year_callback(message, user_id, selected_year):
#     bot.send_message((user_id, f"Selected year: {selected_year}"))


# Polling loop
bot.polling(none_stop=True)

