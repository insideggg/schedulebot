import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime, timedelta
from collections import defaultdict

TOKEN = '6756452663:AAGvRBAbBxFii6e7kgV60FceqSrc0O7SJ-4'
FIREBASE_CREDS_PATH = 'schedulebot-994b3-firebase-adminsdk-kokuq-4c355dd7c3.json'

# Initialize Firebase
cred = credentials.Certificate(FIREBASE_CREDS_PATH)
firebase_app = initialize_app(cred)
db = firestore.client()

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Welcome to ScheduleBot! Use /schedule to create your event")

@bot.message_handler(commands=['schedule'])
def schedule(message):
    user_id = message.chat.id
    bot.send_message(user_id, "Write information about your event in format: ActionName date(YYYY-MM-DD) time(HH:mm)")

    # Set the state to 'schedule_handle'
    bot.register_next_step_handler(message, schedule_handle)

def schedule_handle(message):
    user_id = message.chat.id

    try:
        parts = message.text.split()
        action_name = " ".join(parts[:-2])
        date_str = parts[-2]
        time_str = parts[-1]

        #Create menu
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton('10 min'))
        markup.add(KeyboardButton('15 min'))
        markup.add(KeyboardButton('30 min'))
        markup.add(KeyboardButton('40 min'))

        bot.send_message(user_id, "Choose notification time:", reply_markup=markup)
        bot.register_next_step_handler(message, paste_to_db, action_name, date_str, time_str)
    except ValueError:
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
    except ValueError:
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
    now = datetime.now()
    user_id = message.chat.id

    schedules = db.collection('users').document(str(user_id)).collection('schedules').stream()

    for schedule in schedules:
        schedule_datetime = schedule.get('schedule_datetime')
        notify_minutes_before = schedule.get('notify_minutes_before')

        # Check if it's time to send a notification
        if schedule_datetime - timedelta(minutes=notify_minutes_before) <= now < schedule_datetime:
            bot.send_message(user_id, f"Reminder: {schedule.get('action_name')} is happening in {notify_minutes_before} minutes!")

# Polling loop
bot.polling(none_stop=True)

