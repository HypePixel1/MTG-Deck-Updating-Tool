from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as bs
import re
import os
from datetime import datetime
import shutil

# Convert pasted text into a card dictionary (if possible)
def Text2Dict(text):
    card_dict = {}
    for line in text.splitlines():
        line = line.strip()
        if line:
            match = re.match(r'^(\d+)(?:x )?([^\d]+)', line)
            if match:
                quantity = int(match.group(1))
                name = match.group(2).strip()
                name = re.sub(r'\s*\b[A-Z]{2,3}\b', '', name)
                card_dict[name] = quantity
    return card_dict

# Convert text file into a dictionary with card names as keys and quantity as value
def MakeCardDict(text_path):
    CardDict = {}
    with open(text_path, 'r') as file:
        for i, line in enumerate(file):
                # Get the quantity and the name of each card
                colon_index = line.find(':')
                if colon_index != -1:
                    # Add the card to the dictionary
                    cardName = line[:colon_index]
                    cardQuantity = int(line[colon_index+1:].strip())
                    CardDict[cardName] = cardQuantity
                    #print("Added " + cardName + " to dictionary!")
    
    return CardDict

# Scrape a moxfield profile for public decks and retrieve deck lists for each found
# Saves the deck lists into text files in the /Decks directory
def UpdateCurrentDecks(profile_url):
    # if the user only entered their username, turn it into their profile url
    if (profile_url[0:8] != "https://"):
        profile_url = "https://www.moxfield.com/users/" + profile_url + "/decks/public"

    # Check whether the specified path exists or not
    deck_path = os.getcwd() + "\\Decks"
    if not os.path.exists(deck_path):

        # Create a new directory because it does not exist
        os.makedirs(deck_path)
        print("New deck directory created!")

    # Disable the browser window opening
    options = webdriver.FirefoxOptions()
    options.add_argument('-headless')

    # Create the Firefox driver
    browser = webdriver.Firefox(options=options)
    url = profile_url
    browser.get(url)

    # Wait for an element with class "deckbox" to be present
    print("Searching for decks...")
    wait = WebDriverWait(browser, 10)
    element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "deckbox")))
    source = browser.page_source
    soup = bs(source, "html.parser")

    # Store all found deck titles and links
    decks = []
    count = 0
    deckboxes = soup.find_all('a', class_='deckbox')
    for deckbox in deckboxes:
        count = count + 1
        deck_link = "https://www.moxfield.com/embed" + deckbox['href'][6:]
        deck_title = deckbox.find('span', class_='deckbox-title').text
        decks.append((deck_title, deck_link))
    print("Found " + str(count) + " decks!")

    # Define the pattern to search for card name and quantity
    pattern = r'<td class="text-end">(\d+)</td><td><a class="text-body cursor-pointer no-outline" tabindex="0">([^<]+)</a></td>'

    # For every deck found, grab all cards and write to the text file       
    for deck in decks:
        f = open(deck_path + "\\" + deck[0] + ".txt", "w+")
        print("Opened " + deck[0] + ".txt")
        
        url = deck[1]
        browser.get(url)
        
        # Wait for page to load fully
        wait = WebDriverWait(browser, 10)
        element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table-deck-row")))
        source = browser.page_source
        soup = bs(source, "html.parser")

        # Use regular expressions to find all matches
        matches = re.findall(pattern, str(soup))

        # Write the quantity and name for each match
        count = 0
        for match in matches:
            card_amount, card_name = match
            f.write(card_name + ":" + card_amount + "\n")
            count = count + int(card_amount)
        print("Successfully added " + str(count) + " cards!")
        
        # Close the text file    
        f.close()

    # Close the browser
    browser.quit()
    return

# Keep a copy of the current decks to use as reference in the future    
# Copies over all deck lists into the /SavedDecks directory
def SaveDecks():
    # Delete existing save if there is one
    saved_path = os.getcwd() + "\\SavedDecks"
    if os.path.exists(saved_path):
        shutil.rmtree(saved_path)
    
    # Copy over current decks    
    source_dir = os.getcwd() + "\\Decks"
    destination_dir = os.getcwd() + "\\SavedDecks"
    shutil.copytree(source_dir, destination_dir)
    
    # Create log file to track when save was created
    f = open(saved_path + "\\log.txt", "w+")
    f.write("Retrieved on: " + datetime.now().strftime("%m/%d/%Y %H:%M:%S") + "\n")
    return
    
# Find all changes made to specific deck since last save created    
# Returns a dictionary of card names and quantities
def CompareDecks(fileName):
    # Check whether the specified path exists or not
    path1 = os.getcwd() + "\\Decks\\" + fileName
    path2 = os.getcwd() + "\\SavedDecks\\" + fileName
    if not os.path.exists(path1): 
        print("Deck not found in current decks!")
        return
    if not os.path.exists(path2):
        print("Deck not found in saved decks!")
        saved_deck = {}
    else:
        saved_deck = MakeCardDict("SavedDecks\\" + fileName)
    
    # Convert text files into dictionaries
    current_deck = MakeCardDict("Decks\\" + fileName)
    
    # Find differences in the dictionaries
    diff_dict = {k: current_deck.get(k, 0) - saved_deck.get(k, 0) for k in set(saved_deck) | set(current_deck)}
    
    # Create a new dictionary with only the non-zero entries
    diff_dict_no_zeros = {k: v for k, v in diff_dict.items() if v != 0}
    
    # print("Changes made to " + fileName + " found:")
    # print(diff_dict_no_zeros)
    
    return diff_dict_no_zeros
                    

# Compare the contents of the /Decks and /SavedDecks directories
# Returns a dictionary of card names and quantities
def CompareAllDecks():
    full_diff_dict = {}
    for deck_title in os.listdir("Decks//"):
        if deck_title.endswith('.txt'):
            diff_dict = CompareDecks(deck_title)
            full_diff_dict.update(diff_dict)
            # print("FULL CHANGES MADE:")
            # print(full_diff_dict)
    return full_diff_dict

def LastSavedDate():
    # Get the path to the log file
    log_file_path = os.path.join(os.getcwd(), "SavedDecks", "log.txt")
    
    # Check if the log file exists
    if not os.path.exists(log_file_path):
        return "no log file found!"
    
    # Open the log file in read mode
    with open(log_file_path, "r") as log_file:
        # Read the lines of the file into a list
        lines = log_file.readlines()
        
        # Get the last line of the file
        last_line = lines[-1].strip()
        
        # Extract the date from the last line using a regular expression
        date_pattern = r"Retrieved on: (\d{2}/\d{2}/\d{4})"
        match = re.search(date_pattern, last_line)
        
        # If a match is found, return the date
        if match:
            return match.group(1)
        else:
            return None