from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import requests
import string, re
from bs4 import BeautifulSoup
from collections import defaultdict
import sqlite3 as lite


def filter_eng(s):
    """
    This function filters out all non Coptic words in the input string.
    @param s: input string
    @return: returns a sting of single Coptic word or a list of Coptic words
    """
    ascii = set(string.printable)
    ascii.remove(' ')
    non_eng = list(filter(lambda x: x not in ascii, s))
    non_eng = "".join(non_eng).strip()
    if ' ' in non_eng:
        non_eng = re.split(' +', non_eng)
        return non_eng
    else:
        return non_eng


def detect_cop(line):
    """
    This function detects if the language of the input string is Coptic.
    @param line: a string input
    @return: returns True if the input language is Coptic, and False if the language is not Coptic.
    """

    maxchar = max(line)
    if u'\u2c80' <= maxchar <= u'\u2cff':
        return True
    else:
        return False


class Dictionary(object):
    def __init__(self):
        self.entry = ''
        self.dialect = 'any'
        self.pos = 'any'

    def retrieve_entries(self, entry):
        """
        This function retrieves the unique lexicon ID of the input Coptic token.
        This function is modified from the https://github.com/KELLIA/dictionary/blob/master/results.cgi
        @param entry: the input coptic token
        @return: the ID of the token in Coptic database
        """
        if detect_cop(entry):
            word = entry
            definition = ''
        else:
            word = ''
            definition = entry

        sql_command = 'SELECT * FROM entries WHERE '
        constraints = []
        parameters = []

        if len(word) > 0:
            try:
                re.compile(word)
                op = 'REGEXP'
            except:
                op = '='

            word_search_string = r'.*\n' + word + r'~.*'

            word_constraint = "entries.search " + op + " ?"
            parameters.append(word_search_string)
            if " " in word:
                word_constraint = "(" + word_constraint + " OR entries.oRef = ?)"
                parameters.append(word)
            constraints.append(word_constraint)

        def_search_string = r'.*\b' + definition + r'\b.*'
        try:
            re.compile(def_search_string)
            op = 'REGEXP'
        except:
            op = '='

        def_constraint = "(entries.en " + op + " ? OR entries.de " + op + " ? OR entries.fr " + op + " ?)"
        constraints.append(def_constraint)
        parameters.append(def_search_string)
        parameters.append(def_search_string)
        parameters.append(def_search_string)

        sql_command += " AND ".join(constraints)
        sql_command += " ORDER BY ascii"

        con = lite.connect(
            '/Users/sichang/Documents/AllProjects/Coursework/Fall_2020/Dialogue_System/final_project/dictionary/alpha_kyima_rc1.db')

        con.create_function("REGEXP", 2, lambda expr, item: re.search(expr.lower(), item.lower()) is not None)
        with con:
            cur = con.cursor()
            cur.execute(sql_command, parameters)
            rows = cur.fetchall()

            if len(rows) == 1:
                row = rows[0]
                super_id = str(row[1])
                entry_id = str(row[0])
                tla_id = str(row[12])

                if len(tla_id) > 0:
                    entry_url = "entry.cgi?tla=" + tla_id
                else:
                    entry_url = "entry.cgi?entry=" + entry_id + "&super=" + super_id
                return entry_url
            else:
                return None

    def get_info(self, url):
        """
        This function is used to obtain the meaning, POS tags and morphological information of the Coptic
        words.
        @param url: the result page that contains multiple entries of the input token
        @return: a dictionary contains information of all entries
        """
        info = defaultdict(list)
        soup = BeautifulSoup(url.content, 'lxml')

        table = soup.find('table', 'entrylist')
        if table is None:
            if table is None:
                dic_href = Dictionary.retrieve_entries(self, self.entry)
                dic_href = 'https://coptic-dictionary.org/' + dic_href
                tok_page = requests.get(dic_href)
                tok_info = BeautifulSoup(tok_page.content, 'lxml')

                orth_table = tok_info.find('table', id='orths')
                results = orth_table.contents
                tok = results[1].contents[0].text

                sense_table = tok_info.find('table', id='senses')
                sense = sense_table.find('td', class_='trans')
                if len(sense) > 1:
                    meaning = [i.text for i in sense.contents]
                    meaning = '; '.join(meaning)
                else:
                    meaning = sense.text
                tag = tok_info.find('div', class_='tag').text
                tag = tag.split(':')[1].strip()
                morph = tok_info.find('td', class_='morphology').text
                annis = tok_info.find('td', class_='annis_link').next_element['href']
                info[tok].append((meaning, tag, morph, dic_href, annis))
        else:
            results = table.contents
            href_ls = table.find_all("a", href=True)
            for i, content in enumerate(results):
                content_ls = content.contents
                tok = content_ls[0].text
                sense = content_ls[2].contents
                if len(sense) > 0:
                    sense = sense[0]
                    if len(sense) > 1:
                        meaning = [i.text for i in sense.contents]
                        meaning = '; '.join(meaning)
                    else:
                        meaning = sense.text
                else:
                    meaning = ''
                dic_href = href_ls[i]['href']
                dic_href = 'https://coptic-dictionary.org/' + dic_href

                tok_page = requests.get(dic_href)
                tok_info = BeautifulSoup(tok_page.content, 'lxml')
                tag = tok_info.find('div', class_='tag').text
                tag = tag.split(':')[1].strip()
                morph = tok_info.find('td', class_='morphology').text
                annis = tok_info.find('td', class_='annis_link').next_element['href']
                info[tok].append((meaning, tag, morph, dic_href, annis))

        return info

    def cop_to_eng(self, token):
        """
        This function takes Coptic words as input and returns the search result of that token in online
        dictionary
        @param token: Coptic word
        @return: a string contains the meaning, POS tag and morphological information of the token
        """
        self.entry = token
        dict_URL = 'https://coptic-dictionary.org/results.cgi?coptic={}&dialect={}&pos={}&definition=&def_search_type=exact+sequence&lang=any'.format(
            token, self.dialect, self.pos)
        dict_page = requests.get(dict_URL)

        tok_dict = Dictionary.get_info(self, dict_page)
        output = f'Find following related entries of {token}:\n'
        if len(tok_dict) == 0:
            output = "Sorry, cannot find related entry. Please try another word."
        else:
            idx = 0
            for key in tok_dict:
                if key == token or key == token + '-':
                    for item in tok_dict[key]:
                        idx += 1
                        output += f'{idx}\tMeaning: {item[0]}\tPOS: {item[1]}\tMorphology: {item[2]}\n'
        return output

    def eng_to_cop(self, definition):
        """
        This function takes English word as input and returns the corresponding Coptic entries.
        @param definition: English word
        @return: a sting contains all possible entries of corresponding Coptic words.
        """
        self.entry = definition
        dict_URL = 'https://coptic-dictionary.org/results.cgi?coptic=&dialect={}&pos={}&definition={}&def_search_type=exact+sequence&lang=any'.format(
            self.dialect, self.pos, definition)
        dict_page = requests.get(dict_URL)

        tok_dict = Dictionary.get_info(self, dict_page)
        idx = 0
        output = f'Find following related entries of {definition}:\n'
        if len(tok_dict) == 0:
            output = "Sorry, cannot find related entry. Please try another word."
        else:
            for key in tok_dict:
                for item in tok_dict[key]:
                    if definition in str(item[0]):
                        idx += 1
                        output += f'{idx}\t{key}\t Meaning: {item[0]}\tPOS: {item[1]}\tMorphology: {item[2]}\n'
        return output

    def compare(self, comp1, comp2):
        """
        This function takes two Coptic words as input and returns lexicon information for each word.
        @param comp1: the first Coptic token to compare
        @param comp2: the second Coptic token to compare
        @return: a sting contains lexicon information of both tokens
        """
        output = ''

        for token in [comp1, comp2]:
            dict_URL = 'https://coptic-dictionary.org/results.cgi?coptic={}&dialect={}&pos={}&definition=&def_search_type=exact+sequence&lang=any'.format(
                token, self.dialect, self.pos)
            dict_page = requests.get(dict_URL)

            tok_dict = Dictionary.get_info(self, dict_page)
            output += f'Entries related to {token}:\n'
            idx = 0
            if len(tok_dict) == 0:
                output = f"Sorry, cannot find related entry of {token}. Please try another word.\n"
            else:
                for key in tok_dict:
                    if key == token or key == token + '-':
                        for item in tok_dict[key]:
                            idx += 1
                            output += f'{idx}\tMeaning: {item[0]}\tPOS: {item[1]}\tMorphology: {item[2]}\n'

        return output


class ActionLookup(Action):
    """
    This class is the custom action for the chatbot to run dictionary function.
    """
    def name(self):
        return 'action_lookup'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        # entry = next(tracker.get_latest_entity_values('entry'), 'ⲙⲟⲩⲓ')
        dic = Dictionary()
        text = str(tracker.latest_message.get('text'))
        cop = filter_eng(text)
        if detect_cop(cop):
            output = dic.cop_to_eng(cop)
            dispatcher.utter_message(output)
        dispatcher.utter_message(text='Would you like to make another inquiry?')

        return []


class ActionTranslation(Action):
    """
    This class is the custom action for the chatbot to run translation function.
    """
    def name(self):
        return 'action_translation'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        dic = Dictionary()
        entry = next(tracker.get_latest_entity_values('entry'), None)
        if entry is None:
            dispatcher.utter_message(text='Did not find words to search. Please try to input the word only.')
        else:
            output = dic.eng_to_cop(entry)
            dispatcher.utter_message(output)

        return []


class ActionComparison(Action):
    """
    This class is the custom action for the chatbot to run comparison function.
    """
    def name(self):
        return 'action_comparison'

    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain):
        dic = Dictionary()
        text = str(tracker.latest_message.get('text'))
        entry = filter_eng(text)
        entry = re.split(' +', entry)
        num_entry = len(entry)
        if num_entry == 0:
            dispatcher.utter_message(text='No Coptic found. Please check your input!')
        elif num_entry == 1:
            dispatcher.utter_message(text='Found only one Coptic word. Pleas check your input!')
        elif num_entry > 2:
            dispatcher.utter_message(text='Found more than two Coptic words. Please check your input!')

        compare_1 = entry[0]
        compare_2 = entry[1]

        output = dic.compare(compare_1, compare_2)
        dispatcher.utter_message(output)
        dispatcher.utter_message(text='Would you like to make another inquiry?')

        return []
