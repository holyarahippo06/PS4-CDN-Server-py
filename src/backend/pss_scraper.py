# backend/pss_scraper.py

import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import quote

# The search_playstation_store function is correct and does not need changes.
def search_playstation_store(search_term: str, locale: str = "en-US"):
    encoded_search_term = quote(search_term)
    search_url = f"https://store.playstation.com/{locale}/search/{encoded_search_term}"
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
    print(f"\n--> Searching at: {search_url}")
    response = requests.get(search_url, headers=headers); response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    games_found = []
    product_links = soup.find_all('a', href=re.compile(r'/[a-z]{2}-[a-z]{2}/product/'))
    for link_tag in product_links:
        platform_tags = link_tag.find_all('span', class_='psw-platform-tag')
        is_ps4_game = any('PS4' in tag.get_text() for tag in platform_tags)
        if is_ps4_game:
            name_element = link_tag.find('span', {'data-qa': re.compile(r'#product-name$')})
            name = name_element.get_text().strip() if name_element else "Unknown Title"
            product_id = link_tag['href'].split('/')[-1]
            cusa_match = re.search(r'(CUSA\d{5})', product_id)
            cusa_id = cusa_match.group(1) if cusa_match else "Not Found"
            game_info = { "name": name, "cusa_id": cusa_id, "link": f"https://store.playstation.com{link_tag['href']}" }
            games_found.append(game_info)
    return games_found

# --- MODIFIED: get_game_details now has a robust, multi-format date parser ---
def get_game_details(game_url: str):
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36' }
    print(f"--> Fetching details from: {game_url}")
    response = requests.get(game_url, headers=headers); response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    rating_element = soup.find('div', attrs={'data-qa': 'mfe-game-title#average-rating'})
    rating = rating_element.text.strip() if rating_element else "Not Found"
    description_element = soup.find('p', attrs={'data-qa': 'mfe-game-overview#description'})
    description = description_element.get_text(separator='\n').strip() if description_element else "Not Found"
    publisher_element = soup.find('div', attrs={'data-qa': 'mfe-game-title#publisher'})
    publisher = publisher_element.text.strip() if publisher_element else "Unknown Publisher"
    
    release_date_str = "2024-01-01" # Default fallback date
    try:
        date_element = soup.find('dd', attrs={'data-qa': 'gameInfo#releaseInformation#releaseDate-value'})
        if date_element:
            date_text = date_element.text.strip()
            day, month, year = "", "", ""
            
            # --- NEW: Intelligent Parsing Logic ---
            # Try to parse M/D/YYYY (e.g., 2/4/2014)
            if '/' in date_text:
                parts = date_text.split('/')
                if len(parts) == 3:
                    month, day, year = parts[0], parts[1], parts[2]

            # Else, try to parse D.M.YYYY (e.g., 05.12.2023)
            elif '.' in date_text:
                parts = date_text.split('.')
                if len(parts) == 3:
                    day, month, year = parts[0], parts[1], parts[2]
            
            # If we successfully parsed a date, format it correctly
            if all([day, month, year]):
                # Handle 2-digit years if they ever appear
                if len(year) == 2:
                    year = "20" + year
                # Format to YYYY-MM-DD with zero-padding
                release_date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    except Exception as e:
        # If any part of the date parsing fails, log it and use the default.
        print(f"    [!] Could not parse date. Error: {e}")
        pass

    return {"rating": rating, "description": description, "publisher": publisher, "release_date": release_date_str}