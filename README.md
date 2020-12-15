# Language_Learning_Chatbot_for_Coptic
This project aims to develop a language learning chatbot for 
Coptic, a low-resourced historical language in Egypt. It allows 
users to ask four types of questions, namely culture, dictionary, 
translation and comparison.

## Requirements
To use this system, Rasa version 2.0 is required. Please use the 
following command (requires Python 3.6, 3.7 or 3.8) to download it:

`pip3 install rasa`

## Example Usage
After installing Rasa 2.0, you can start to play with the chatbot. 
Go to the downloaded directory of this project and follows:

* `rasa train` It trains the NLU data and core module of Rasa.
* `rasa run actions & rasa shell` It starts the action server and open the 
interface of chatbot in the commandline.
  
Now you should be able to start chatting with the chatbot!