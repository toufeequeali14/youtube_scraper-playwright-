from playwright.sync_api import sync_playwright
import time
import pandas as pd
from datetime import datetime
import re

def clean_text(text):
    """Clean and normalize text"""
    if text is None:
        return ""
    return ' '.join(text.split()).strip()

def extract_subscriber_count(text):
    """Extract subscriber count from text"""
    if not text or text == "Unknown Subscribers":
        return text
    # Remove any extra text and keep just the number + unit
    text = text.lower()
    match = re.search(r'([\d.]+\s*[kmb]?)\s*subscriber', text)
    if match:
        return match.group(1).strip()
    return text

def get_user_input():
    """Get user input for channel URL and scroll settings"""
    print("="*70)
    print("YOUTUBE CHANNEL SCRAPER - CONFIGURATION")
    print("="*70)
    
    # Get channel URL
    channel_url = input("Paste the YouTube channel URL: ").strip()
    while not channel_url:
        print("❌ URL cannot be empty!")
        channel_url = input("Paste the YouTube channel URL: ").strip()
    
    # Get scroll settings
    print("\nScroll Options:")
    print("1. Limited scrolls (custom number)")
    print("2. All scrolls (load all videos)")
    
    scroll_choice = input("Choose scroll option (1 or 2): ").strip()
    
    if scroll_choice == "1":
        try:
            max_scroll_attempts = int(input("Enter number of scrolls: ").strip())
            if max_scroll_attempts <= 0:
                print("⚠ Using default 10 scrolls")
                max_scroll_attempts = 10
        except ValueError:
            print("⚠ Invalid input. Using default 10 scrolls")
            max_scroll_attempts = 10
    else:
        max_scroll_attempts = 100  # Very high number for "all scrolls"
        print("✓ Selected: All scrolls (load all available videos)")
    
    return channel_url, max_scroll_attempts

def run_playwright():
    # Get user input
    channel_url, max_scroll_attempts = get_user_input()
    
    # Extract channel handle from URL
    channel_handle = channel_url.rstrip('/').split('/')[-1]
    if '?' in channel_handle:
        channel_handle = channel_handle.split('?')[0]
    
    print(f"\nChannel Handle: {channel_handle}")
    print(f"Max Scrolls: {'All' if max_scroll_attempts == 100 else max_scroll_attempts}")
    print("="*70)

    # Initialize variables
    channel_name = "Unknown Channel"
    sub_count = "Unknown Subscribers"
    channel_description = "No description available"
    video_count = "Unknown"
    join_date = "Unknown"
    total_views = "Unknown"

    with sync_playwright() as p:
        # Launch browser with options
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        # Create context with viewport
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        # Add script to hide automation
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """)
        
        page = context.new_page()
        
        # =============================================================================
        # STEP 1: EXTRACT CHANNEL INFORMATION FROM ABOUT PAGE
        # =============================================================================
        print("\n" + "="*70)
        print("STEP 1: EXTRACTING CHANNEL INFORMATION")
        print("="*70)

        try:
            # Navigate to About page
            about_url = f"https://www.youtube.com/{channel_handle}/about"
            print(f"Navigating to: {about_url}")
            page.goto(about_url, wait_until='networkidle')
            page.wait_for_timeout(3000)
            
            # Extract Channel Name from page title first
            page_title = page.title()
            if " - YouTube" in page_title:
                channel_name = page_title.replace(" - YouTube", "").strip()
                print(f"✓ Channel Name: {channel_name}")
            
            # Try to get channel name from header
            try:
                name_element = page.wait_for_selector("ytd-channel-name yt-formatted-string, #channel-name yt-formatted-string", timeout=10000)
                if name_element and name_element.text_content().strip():
                    channel_name = clean_text(name_element.text_content())
                    print(f"✓ Channel Name (verified): {channel_name}")
            except:
                pass
            
            # Extract Subscriber Count
            print("\nSearching for subscriber count...")
            
            # Multiple methods to find subscriber count
            sub_selectors = [
                "yt-formatted-string#subscriber-count",
                "#subscriber-count",
                "span.yt-core-attributed-string",
                ".yt-core-attributed-string--link-inherit-color"
            ]
            
            for selector in sub_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for element in elements:
                        sub_text = clean_text(element.text_content())
                        if sub_text and "subscriber" in sub_text.lower():
                            sub_count = extract_subscriber_count(sub_text)
                            print(f"✓ Subscribers: {sub_count}")
                            break
                    if sub_count != "Unknown Subscribers":
                        break
                except:
                    continue
            
            # Method: Look in page source as last resort
            if sub_count == "Unknown Subscribers":
                try:
                    page_source = page.content()
                    matches = re.findall(r'"subscriberCountText".*?"simpleText":"([^"]+)"', page_source)
                    if matches:
                        sub_count = extract_subscriber_count(matches[0])
                        print(f"✓ Subscribers: {sub_count} (from page source)")
                except Exception as e:
                    print(f"⚠ Could not find subscriber count: {e}")
            
            # Extract Channel Description
            print("\nSearching for channel description...")
            try:
                desc_element = page.wait_for_selector("#description-container", timeout=10000)
                if desc_element:
                    desc_text = clean_text(desc_element.text_content())
                    if desc_text and len(desc_text) > 10:
                        channel_description = desc_text
                        print(f"✓ Description extracted ({len(channel_description)} characters)")
            except:
                print("⚠ Could not find channel description")
            
            # Extract Detailed Statistics
            print("\nSearching for channel statistics...")
            try:
                # Look for all statistics
                stats_elements = page.query_selector_all("#right-column yt-formatted-string")
                for element in stats_elements:
                    text = clean_text(element.text_content())
                    
                    # Look for video count
                    if "video" in text.lower() and not video_count.isdigit():
                        match = re.search(r'([\d,]+)\s*video', text, re.IGNORECASE)
                        if match:
                            video_count = match.group(1).replace(',', '')
                            print(f"✓ Total Videos: {video_count}")
                    
 
                        
            except Exception as e:
                print(f"⚠ Could not extract all statistics: {e}")

        except Exception as e:
            print(f"⚠ Error extracting channel information: {str(e)}")

        # =============================================================================
        # STEP 2: EXTRACT VIDEO DATA FROM VIDEOS TAB
        # =============================================================================
        print("\n" + "="*70)
        print("STEP 2: EXTRACTING VIDEO DATA")
        print("="*70)

        try:
            # Navigate to Videos page
            videos_url = f"https://www.youtube.com/{channel_handle}/videos"
            print(f"Navigating to: {videos_url}")
            page.goto(videos_url, wait_until='networkidle')
            page.wait_for_timeout(3000)
            
            # Check if we're on the right page
            current_url = page.url
            print(f"Current URL: {current_url}")
            
            if channel_handle not in current_url:
                print("⚠ Warning: Not on the expected channel page!")
            
            # Scroll to load videos
            print(f"\nScrolling to load videos ({'All' if max_scroll_attempts == 100 else max_scroll_attempts} scrolls)...")
            scroll_attempts = 0
            no_change_count = 0
            last_video_count = 0
            
            while scroll_attempts < max_scroll_attempts and no_change_count < 3:
                # Scroll down
                page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight);")
                page.wait_for_timeout(2000)
                
                # Check how many videos are loaded so far
                try:
                    current_videos = len(page.query_selector_all("ytd-rich-item-renderer"))
                    print(f"Scroll {scroll_attempts + 1}/{max_scroll_attempts} - Videos loaded: {current_videos}")
                    
                    if current_videos == last_video_count:
                        no_change_count += 1
                        if no_change_count >= 3:
                            print("✓ No new videos loaded after 3 attempts. Stopping scroll.")
                            break
                    else:
                        no_change_count = 0
                    
                    last_video_count = current_videos
                except Exception as e:
                    print(f"Scroll {scroll_attempts + 1}/{max_scroll_attempts} - Error counting videos: {e}")
                
                scroll_attempts += 1
                
                # For "all scrolls" mode, break if we've scrolled a lot and no new content
                if max_scroll_attempts == 100 and scroll_attempts >= 50 and no_change_count >= 2:
                    print("✓ Reached end of content in 'all scrolls' mode.")
                    break
            
            print(f"✓ Scrolling complete! Total scrolls: {scroll_attempts}")
            print(f"✓ Total videos loaded: {last_video_count}\n")
            
            # Extract video data
            video_data = []
            
            print("Extracting video information...")
            
            # Wait for videos to load
            video_elements = page.query_selector_all("ytd-rich-item-renderer")
            
            print(f"Found {len(video_elements)} video elements\n")
            
            for i, video in enumerate(video_elements, 1):
                try:
                    # Get title and URL
                    title_element = video.query_selector("#video-title-link, #video-title")
                    if not title_element:
                        continue
                        
                    title = clean_text(title_element.text_content())
                    video_url = title_element.get_attribute("href")
                    
                    # Skip if no title
                    if not title:
                        continue
                    
                    # Get metadata (views and upload date)
                    view_count = "N/A"
                    upload_date = "N/A"
                    
                    try:
                        metadata_elements = video.query_selector_all("#metadata-line span")
                        if len(metadata_elements) >= 1:
                            view_count = clean_text(metadata_elements[0].text_content())
                        if len(metadata_elements) >= 2:
                            upload_date = clean_text(metadata_elements[1].text_content())
                    except:
                        pass
                    
                    # Get duration
                    duration = "N/A"
                    try:
                        duration_element = video.query_selector("span.style-scope.ytd-thumbnail-overlay-time-status-renderer")
                        if duration_element:
                            duration = clean_text(duration_element.text_content())
                    except:
                        pass
                    
                    video_data.append({
                        'channel_name': channel_name,
                        'title': title,
                        'views': view_count,
                        'upload_date': upload_date,
                        'duration': duration,
                        'url': video_url
                    })
                    
                    if i % 10 == 0:
                        print(f"✓ Extracted {i} videos...")
                
                except Exception as e:
                    continue
            
            print(f"\n✓ Total videos extracted: {len(video_data)}")

        except Exception as e:
            print(f"⚠ Error extracting videos: {str(e)}")
            import traceback
            traceback.print_exc()

        # Update video count if not found earlier
        if video_count == "Unknown" and video_data:
            video_count = str(len(video_data))

        # =============================================================================
        # DISPLAY COMPREHENSIVE SUMMARY
        # =============================================================================
        print("\n" + "="*70)
        print("COMPREHENSIVE CHANNEL SUMMARY")
        print("="*70)
        print(f"📺 Channel Name:       {channel_name}")
        print(f"👥 Subscribers:        {sub_count}")
        print(f"📊 Total Videos:       {video_count}")
        # print(f"👀 Total Views:        {total_views}")
        # print(f"📅 Join Date:          {join_date}")
        print(f"🎬 Videos Scraped:     {len(video_data)}")
        print(f"🔗 Channel Handle:     {channel_handle}")
        print(f"🌐 Channel URL:        {channel_url}")
        print("\n" + "📝 CHANNEL DESCRIPTION:")
        print("-" * 50)
        if channel_description != "No description available" and len(channel_description) > 10:
            # Print description with word wrap
            words = channel_description.split()
            lines = []
            current_line = ""
            
            for word in words:
                if len(current_line + " " + word) <= 80:
                    current_line += " " + word
                else:
                    lines.append(current_line.strip())
                    current_line = word
            if current_line:
                lines.append(current_line.strip())
            
            for line in lines:
                print(f"  {line}")
            print(f"\n  Total description length: {len(channel_description)} characters")
            print(f"  Total words: {len(words)}")
        else:
            print("  No description available or description too short")
        print("="*70)

        # =============================================================================
        # SAVE DATA TO CSV FILES
        # =============================================================================
        print("\nSaving data...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean_channel_name = "".join(c for c in channel_name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not clean_channel_name or clean_channel_name == "UnknownChannel":
                clean_channel_name = channel_handle
            
            # Save video data
            if video_data:
                df = pd.DataFrame(video_data)
                video_filename = f"videos_{clean_channel_name}_{timestamp}.csv"
                df.to_csv(video_filename, index=False, encoding='utf-8-sig')
                print(f"✓ Video data saved: {video_filename}")
            else:
                print("⚠ No video data to save")
            
            # Save channel info
            channel_info = {
                'channel_name': [channel_name],
                'channel_handle': [channel_handle],
                'subscribers': [sub_count],
                'total_videos': [video_count],
                'total_views': [total_views],
                # 'join_date': [join_date],
                'videos_scraped': [len(video_data)],
                'description': [channel_description],
                'description_length': [len(channel_description)],
                'description_words': [len(channel_description.split())],
                'scraped_at': [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                'channel_url': [channel_url],
                'scrolls_used': [scroll_attempts]
            }
            
            channel_df = pd.DataFrame(channel_info)
            channel_filename = f"channel_info_{clean_channel_name}_{timestamp}.csv"
            channel_df.to_csv(channel_filename, index=False, encoding='utf-8-sig')
            print(f"✓ Channel info saved: {channel_filename}")
            
        except Exception as e:
            print(f"⚠ Error saving data: {str(e)}")
            import traceback
            traceback.print_exc()

        # Close browser
        browser.close()
        print("\n✓ Browser closed")

# Run the Playwright script
if __name__ == "__main__":
    run_playwright()
    print("="*70)
    print("SCRAPING COMPLETE!")
    print("="*70)