import telebot
from bs4 import BeautifulSoup
from telebot import types
import pandas as pd
import numpy as np
import requests

from fuzzywuzzy import process
from fuzzywuzzy import fuzz


def export_to_csv():
    global settings_global, weights
    pd.DataFrame([(str(settings_global.get('cluster_numbers')), ';'.join([str(x) for x in weights]))],
                 columns=['num_clust', 'clust_weights']).to_excel('data/settings.xlsx')


def make_text(results, show_first_line = True):
    if show_first_line:
        text = "Наилучшие производители (по убыванию рейтинга):\n"
    else:
        text = ""
    for index, row in results.iterrows():
        if not pd.isnull(row['name']):
            text += "<b>Название производителя:</b> " + str(row['name']) + "\n"
        if not pd.isnull(row['site']):
            text += "<b>Сайт производителя:</b> " + str(row['site']) + "\n"
        if not pd.isnull(row['place_fail_rel_size']):
            text += "<b>Вероятность наступления нарушения:</b> " + "{0:.2f}".format(
                float(row['place_fail_rel_size']) * 100) + "% \n"
        if not pd.isnull(row['google_rating']):
            text += "<b>Google рейтинг:</b> " + (int(row['google_rating']) * '🌟' + '\n')

        if not pd.isnull(row['severity']):
            text += "<b>Тяжесть нарушения:</b> "
            if float(row['severity']) > 0.85:
                text += "тяжелая \n"
            elif float(row['severity']) > 0.6:
                text += "средняя \n"
            else:
                text += "легкая \n"

        text += "====================  \n"
    return text


def make_text_man(results, expert):
    text = ""
    if results.shape[0] == 0:
        return ""
    for i, row in results.iterrows():
        for j, row_expert in expert.iterrows():

            if not pd.isnull(row['name']):
                text += "<b>Название производителя:</b> " + str(row['name']) + "\n"
            if not pd.isnull(row['site']):
                text += "<b>Сайт:</b> " + str(row['site']) + "\n"
            if not pd.isnull(row['rating']):
                text += "<b>Рейтинг:</b> " + str(np.round(row['rating'], 2) * 100) + "\n"
            if not pd.isnull(row_expert['Нарушения экспертно']):
                exp_sum = row_expert['Тяжесть нарушения экспертно']
                text += "<b>Экспертная оценка нарушений:</b> " + str(exp_sum) + "\n"
                text += "<b>Выявленные нарушения:</b> " + row_expert['Нарушения экспертно'] + "\n"
            if not pd.isnull(row['place_fail_rel_size']):
                text += "<b>Вероятность наступления нарушения:</b> " + "{0:.2f}".format(
                    float(row['place_fail_rel_size']) * 100) + "%"
                if row['trend'] == 1:
                    text += ' ↗'
                elif row['trend'] == -1:
                    text += ' ↘'
                text += '\n'
            if not pd.isnull(row['place_total_fail']):
                text += "<b>Количество препаратов с нарушениями:</b> " + str(int(row['place_total_fail'])) + '\n'
            if not pd.isnull(row['Скорость реагирования']):
                text += "<b>Среднее время устранения нарушений:</b> " + str(int(row['Скорость реагирования'])) + ' дней\n'
            if not pd.isnull(row['google_rating']):
                text += "<b>Google рейтинг:</b> " + int(row['google_rating']) * '🌟' + '\n'
            if not pd.isnull(row['link_numbers']):
                text += "<b>Цитируемость:</b> " + str(int(row['link_numbers'])) + '\n'

            text += "====================  \n"

            break

    return text


token = ''
bot = telebot.TeleBot(token)
user_state = None
weights = []

settings_global = {
    "cluster_numbers": None
}

dict_medicines = pd.read_csv('data/gos_dict.csv', sep=';', encoding='cp1251', names=['place_id', 'place_name', 'name'], skiprows=1)
dict_medicines = dict_medicines[~pd.isnull(dict_medicines.place_id)]
dict_medicines.reset_index(inplace=True, drop=True)

expert = pd.read_csv('data/expert.csv', encoding='cp1251')

# dict_manufacturers = pd.read_csv('data/gos_dict_manuf.csv', sep=';', encoding='cp1251', names=['place_id', 'name'],
#                                  skiprows=1)
# dict_manufacturers = dict_manufacturers[~pd.isnull(dict_manufacturers.place_id)]
# dict_manufacturers.reset_index(inplace=True, drop=True)

results = pd.read_csv('results/result_pan.csv', sep=';', encoding='cp1251')


@bot.message_handler(commands=["menu"])
def menu(message):
    keyboard_menu = types.ReplyKeyboardMarkup(row_width=0.5, resize_keyboard=True)
    keyboard_menu.row('Настройки', 'Рейтинг')
    keyboard_menu.row('Поиск по производителю', 'Поиск по МНН')
    bot.send_message(message.chat.id, "Выберите пункт меню:", reply_markup=keyboard_menu)


@bot.message_handler(func=lambda message: message.text == "Настройки")
def settings(m):
    keyboard_hider = types.ReplyKeyboardRemove()
    global user_state, weights
    weights = []
    user_state = 'settings'
    bot.send_message(m.chat.id, "Вы перешли в настройки. Введите количество классов отзывов (от 2 до 5):",
                     reply_markup=keyboard_hider)


@bot.message_handler(func=lambda message: message.text == "Рейтинг")
def rating(m):
    keyboard_hider = types.ReplyKeyboardRemove()
    global user_state
    user_state = 'print_rating'
    # bot.send_message(m.chat.id, "Тут будет рейтинг!", reply_markup=keyboard_hider)
    result_df = results.sort_values(['rating'], ascending=True)[:5]
    bot.send_message(m.chat.id, make_text(result_df, False), parse_mode='html')
    user_state = None
    menu(m)


@bot.message_handler(commands=["start"])
def start(message):
    global user_state
    user_state = None
    bot.send_message(message.chat.id, "Приветствуем вас в боте Протека хакатона AI.Hack Москва! ")
    menu(message)


@bot.message_handler(func=lambda message: message.text == "Поиск по производителю")
def search_man(m):
    keyboard_hider = types.ReplyKeyboardRemove()
    global user_state
    user_state = 'search_man'
    bot.send_message(m.chat.id, "Введите производителя:", reply_markup=keyboard_hider)


@bot.message_handler(func=lambda message: user_state == 'settings')
def settings_n_cluster(m):
    global user_state, settings_global

    if not m.text.isdigit():
        # Состояние не меняем, поэтому только выводим сообщение об ошибке и ждём дальше
        bot.send_message(m.chat.id, "Что-то не так, попробуй ещё раз!")
        return

    if int(m.text) < 2 or int(m.text) > 5:
        bot.send_message(m.chat.id, "Недопустимое количество классов. Введите от 2 до 5.")
        return
    else:
        settings_global['cluster_numbers'] = int(m.text)
        user_state = 'settings_1'
        bot.send_message(m.chat.id, "Введите веса для " + str(
            m.text) + " классов. Классы упорядочены по возрастанию степени тяжести нарушений. Вес для первого класса (с наименее тяжкими нарушениями):")


@bot.message_handler(func=lambda message: message.text == "Поиск по МНН")
def search_mnn(m):
    keyboard_hider = types.ReplyKeyboardRemove()
    global user_state
    user_state = 'search_mnn'
    bot.send_message(m.chat.id, "Введите наименование МНН:", reply_markup=keyboard_hider)


@bot.message_handler(func=lambda message: user_state == 'settings_1')
def settings_weights(m):
    global user_state, settings_global, weights

    if not m.text.isdigit():
        # Состояние не меняем, поэтому только выводим сообщение об ошибке и ждём дальше
        bot.send_message(m.chat.id, "Что-то не так, попробуй ещё раз!")
        return
    else:
        weights.append(int(m.text))
        if len(weights) < settings_global['cluster_numbers']:
            bot.send_message(m.chat.id, "Введите вес для " + str(len(weights) + 1) + " класса:")
            return
        else:
            user_state = None
        bot.send_message(m.chat.id, "Настройка закончена.")
        export_to_csv()

        menu(m)


def get_rigla_request(keyword):
    return 'http://www.rigla.ru/search/?q=' + str(keyword.replace(' ', '+'))


def find_in_rigla(keyword):
    url = get_rigla_request(keyword)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
    }

    r = requests.get(url, headers=headers)

    soup = BeautifulSoup(r.text.encode('utf8'), "lxml")

    prices = []
    for price in soup.findAll('span', {'class': 'price'}):
        if price.text == "":
            break
        l = [np.round(float(s.replace(',', '.')), 1) for s in price.text.split() if s.isdigit()]
        if len(l) > 0:
            prices.append(l[0])
    if len(prices) == 0:
        return None
    if len(prices) == 1:
        return str(prices[0])
    elif len(prices) > 1:
        return str(min(prices)) + ' - ' + str(max(prices))


@bot.message_handler(func=lambda message: user_state == 'search_mnn')
def search_mnn(m):
    global dict_medicines
    search_result = pd.DataFrame(
        process.extract(m.text, dict_medicines.name, scorer=fuzz.token_sort_ratio, limit=10000))
    if len(search_result[search_result[1] > 75]) > 0:
        l = str(search_result.loc[0, 0])
        url = get_rigla_request(l)
        price = find_in_rigla(l)
        keyboard = types.InlineKeyboardMarkup()
        url_button = types.InlineKeyboardButton(text="Найти на Ригле", url=url)
        keyboard.add(url_button)
        if price is None:
            bot.send_message(m.chat.id, "Найдено лекарство: " + l
                             + '. Наилучшие производители (по убыванию рейтинга):', parse_mode='html',
                             reply_markup=keyboard)
        else:
            bot.send_message(m.chat.id, "Найдено лекарство: " + l + ", цена: " + price + ' руб'
                             + '. Наилучшие производители (по убыванию рейтинга):', parse_mode='html',
                             reply_markup=keyboard)

        search_result = dict_medicines.iloc[search_result[search_result[1] > 75].set_index(2).index.values]
        result_df = results[results.place_id.isin(search_result.place_id)].sort_values(by='rating', ascending=True)[:10]
        bot.send_message(m.chat.id, make_text(result_df), parse_mode='html')

    else:
        bot.send_message(m.chat.id, "Ничего не найдено, попробуйте еще раз. \n <b>Еще раз попробуйте</b>",
                         parse_mode='html')
    user_state = None
    menu(m)


@bot.message_handler(func=lambda message: user_state == 'search_man')
def search_man(m):
    global dict_medicines
    search_result = pd.DataFrame(
        process.extract(m.text, dict_medicines.place_name, scorer=fuzz.token_sort_ratio, limit=1))
    if len(search_result) > 0:
        bot.send_message(m.chat.id, "Найден производитель: " + str(search_result.loc[0, 0]), parse_mode='html')
        search_result = dict_medicines.iloc[search_result.loc[0, 2]]
        result_df = results[results.place_id == search_result.place_id]  # [:1]
        expert_df = expert[expert.place_id == search_result.place_id]  # [:1]
        t = make_text_man(result_df, expert_df)
        if t == "":
            bot.send_message(m.chat.id, "Информация не найдена.", parse_mode='html')
        else:
            bot.send_message(m.chat.id, t, parse_mode='html')

    else:
        bot.send_message(m.chat.id, "Ничего не найдено, попробуйте еще раз. \n <b>Еще раз попробуйте</b>",
                         parse_mode='html')
    user_state = None
    menu(m)


bot.polling(none_stop=True)
