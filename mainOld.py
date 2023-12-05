import threading
import time
from datetime import datetime, timedelta
import telebot

user_schedules = {}
user_notifications = {}

TOKEN = 'BOT_TOKEN'

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome to Schedule Bot! Use /schedule to start.")

@bot.message_handler(commands=['schedule'])
def schedule(message):
    user_id = message.chat.id
    bot.reply_to(message, "Write you event name and time.")
    bot.register_next_step_handler(message, schedule_handle)
    # schedule_message = " ".join(message.text.split()[1:])
    # user_schedules[user_id] = schedule_message
    # bot.reply_to(message, f"Your event has been set to: {schedule_message}")

def schedule_handle(message):
    user_id = message.chat.id

    parts = message.text.split()
    action_name = parts[:-2]
    date_str = parts[-2]
    time_str = parts[-1]

    try:
        if user_id not in user_schedules:
            user_schedules[user_id] = {}

        if date_str not in user_schedules:
            user_schedules[user_id][date_str] = []
        user_schedules[user_id][date_str].append((action_name, time_str))

        bot.send_message(user_id, f"Your event has been saved for {date_str}!")
    except ValueError:
        bot.send_message(user_id, "Invalid date format. Please try again!")

@bot.message_handler(commands=['getschedule'])
def get_schedule(message):
    user_id = message.chat.id

    if user_id in user_schedules:
        schedule_text = "Your schedule:\n"
        for date_str, event_list in user_schedules[user_id].items():
            schedule_text += f"\n{date_str}:\n"
            for event in event_list:
                action_name, time_str = event
                schedule_text += f"{str(action_name)} at {time_str}\n"
        bot.send_message(user_id, schedule_text)
    else:
        bot.send_message(user_id, "You haven't scheduled any events yet.")

    # if user_id in user_schedules:
    #    bot.reply_to(message, f"Your current schedule is: {user_schedules[user_id]}")
    # else:
    #    bot.reply_to(message, "Create your event first!")

@bot.message_handler(commands=['notifyme'])
def notify_me(message):
    user_id = message.chat.id
    args = message.text.split()[1:]
    if len(args) < 2:
        bot.reply_to(message, "Usage: /notifyme action_name minutes_before_event")
        return

    action_name = args[0]
    minutes_before_event = int(args[1])

    # Count notification time
    notification_time = datetime.now() + timedelta(minutes=minutes_before_event)

    user_notifications[user_id] = (action_name, notification_time)

    bot.reply_to(message, f"Notification has been set for {action_name} / {minutes_before_event} before the event. "
                          f"The bot will send you a reminder message!")

def check_notification():
    now = datetime.now()

    for user_id, (action_name, notification_time) in user_notifications.items():
        if now >= notification_time:
            bot.send_message(user_id, f"Reminder, {action_name} is happening right now!")

if __name__ == '__main__':
    # Start the thread for checking notifications
    notification_thread = threading.Thread(target=lambda: bot.polling(none_stop=True))
    notification_thread.start()

    # Run the check_notification function every minute
    while True:
        check_notification()
        time.sleep(60)




