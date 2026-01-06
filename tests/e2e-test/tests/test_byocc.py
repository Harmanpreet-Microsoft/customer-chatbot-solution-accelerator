import logging
import time
import pytest
import io
import os
import json
from datetime import datetime

from config.constants import *
from pages.webUserPage import WebUserPage

logger = logging.getLogger(__name__)


@pytest.mark.test_id("28907")
class TestBYOCCGoldenPath:
    
    def _take_screenshot(self, page, name_suffix):
        """Helper method to take screenshots during test execution"""
        try:
            screenshots_dir = os.path.join(os.path.dirname(__file__), "..", "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(screenshots_dir, f"test_golden_path_{name_suffix}_{timestamp}.png")
            
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info(f"Screenshot taken: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logger.error(f"Failed to take screenshot {name_suffix}: {str(e)}")
            return None
    """Test class for BYOCC Customer Chatbot Golden Path demo script"""

    def test_golden_path_demo_script(self, page):
        """
        Test ID: 28907 
        Title: Golden Path- BYOCC - Customer Chatbot - test golden path demo script works properly
        
        This test validates the complete golden path demo script:
        1. Opens the URL
        2. Opens chat window  
        3. Tests paint color query and validates response
        4. Tests color matching service query
        5. Tests warranty query
        6. Tests color dissatisfaction query
        """
        
        # Initialize page object
        web_user_page = WebUserPage(page)
        
        # Navigate to the application URL
        page.goto(WEB_URL)
        logger.info(f"Navigated to URL: {WEB_URL}")
        
        # Wait for page to load
        page.wait_for_load_state("domcontentloaded")
        
        # Take initial screenshot
        self._take_screenshot(page, "01_initial_page")
        
        # Step 1: Open chat window
        logger.info("Opening chat window...")
        web_user_page.open_chat_window()
        
        # Take screenshot after opening chat
        self._take_screenshot(page, "02_chat_opened")
        
        # Load test data
        with open(json_file_path, "r") as file:
            test_data = json.load(file)
            questions_data = test_data["questions"]
        
        try:
            # Step 2: Test blue paint query
            logger.info("Testing blue paint color query...")
            blue_paint_data = next(q for q in questions_data if q["id"] == "blue_paint_query")
            
            response, contains_expected, found_keyword = web_user_page.ask_question_and_verify(
                blue_paint_data["question"], 
                blue_paint_data["expected_responses"]
            )
            
            # Take screenshot after blue paint query
            self._take_screenshot(page, "03_blue_paint_query")
            
            assert contains_expected, f"Response did not contain expected content. Response: {response}"
            logger.info(f"✓ Blue paint query successful. Found keyword: {found_keyword}")
            
            # Step 3: Test color matching service query
            logger.info("Testing color matching service query...")
            color_matching_data = next(q for q in questions_data if q["id"] == "color_matching_service")
            
            response, contains_expected, found_keyword = web_user_page.ask_question_and_verify(
                color_matching_data["question"],
                color_matching_data["expected_responses"]
            )
            
            # Take screenshot after color matching query
            self._take_screenshot(page, "04_color_matching_query")
            
            assert contains_expected, f"Color matching response did not contain expected content. Response: {response}"
            logger.info(f"✓ Color matching query successful. Found keyword: {found_keyword}")
            
            # Step 4: Test warranty query
            logger.info("Testing warranty query...")
            warranty_data = next(q for q in questions_data if q["id"] == "warranty_info")
            
            response, contains_expected, found_keyword = web_user_page.ask_question_and_verify(
                warranty_data["question"],
                warranty_data["expected_responses"]
            )
            
            # Take screenshot after warranty query
            self._take_screenshot(page, "05_warranty_query")
            
            assert contains_expected, f"Warranty response did not contain expected content. Response: {response}"
            logger.info(f"✓ Warranty query successful. Found keyword: {found_keyword}")
            
            # Step 5: Test color dissatisfaction query (final question - may need extra time)
            logger.info("Testing color dissatisfaction query...")
            dissatisfaction_data = next(q for q in questions_data if q["id"] == "color_dissatisfaction")
            
            # Clear input and ensure fresh start for final question
            text_area = page.locator(web_user_page.TYPE_QUESTION_TEXT_AREA)
            text_area.click()
            text_area.fill("")
            
            # Enter the question
            web_user_page.enter_a_question(dissatisfaction_data["question"])
            
            # Wait longer for this question as it may involve more complex processing
            page.wait_for_timeout(3000)
            
            # Click send button
            web_user_page.click_send_button()
            
            # Extended wait for final response (policy questions may take longer)
            web_user_page.wait_for_response(timeout=60000)  # 60 seconds
            
            # Extra wait to ensure response is fully loaded
            page.wait_for_timeout(8000)
            
            # Get response with multiple attempts if needed
            response = ""
            for attempt in range(3):
                response = web_user_page.get_last_response()
                if any(keyword.lower() in response.lower() for keyword in dissatisfaction_data["expected_responses"]):
                    break
                logger.info(f"Attempt {attempt + 1}: Waiting longer for dissatisfaction response...")
                page.wait_for_timeout(5000)
            
            # Take screenshot after final query
            self._take_screenshot(page, "06_final_query")
            
            contains_expected, found_keyword = web_user_page.verify_response_contains_keywords(response, dissatisfaction_data["expected_responses"])
            
            assert contains_expected, f"Color dissatisfaction response did not contain expected content. Response: {response}"
            logger.info(f"✓ Color dissatisfaction query successful. Found keyword: {found_keyword}")

            logger.info("🎉 Golden Path demo script test completed successfully!")
            
        except Exception as e:
            # Take screenshot on any failure
            self._take_screenshot(page, f"FAILURE_{datetime.now().strftime('%H%M%S')}")
            logger.error(f"Test failed with error: {str(e)}")
            raise e

    @pytest.mark.test_id("28940")
    def test_chat_message_visible_immediately_after_sending(self, page):
        """
        Test ID: 28940
        Test Name: BUG 28572-BYOCC - Customer Chatbot - Chat Message Should Be Visible Immediately After Sending
        Description: Verify that chat messages are immediately visible after sending without any delay or hiding
        
        Test Steps:
        1. Launch the Web Application - Web Application loads successfully
        2. Open the Chat Panel - Chat Panel opens successfully  
        3. Enter any question in the chat input box - Text is entered successfully
        4. Click the Send button - The sent question is immediately visible in the chat panel
        5. Observe the chat area immediately after sending - Chat message is not hidden or invisible at any time
        """
        web_user_page = WebUserPage(page)
        test_question = "What blue paint colors do you have?"
        
        try:
            # Step 1: Launch the Web Application
            logger.info("Step 1: Launching Web Application...")
            page.goto(WEB_URL)
            page.wait_for_load_state("domcontentloaded")
            logger.info(f"✓ Web Application loaded successfully: {WEB_URL}")
            
            # Take initial screenshot
            self._take_screenshot(page, "message_visibility_01_app_loaded")
            
            # Step 2: Open the Chat Panel
            logger.info("Step 2: Opening Chat Panel...")
            web_user_page.open_chat_window()
            page.wait_for_timeout(2000)  # Wait for chat to fully open
            logger.info("✓ Chat Panel opened successfully")
            
            # Take screenshot after opening chat
            self._take_screenshot(page, "message_visibility_02_chat_opened")
            
            # Step 3: Enter question in the chat input box
            logger.info("Step 3: Entering question in chat input box...")
            text_area = page.locator(web_user_page.TYPE_QUESTION_TEXT_AREA)
            text_area.click()
            text_area.fill(test_question)
            
            # Verify text was entered
            entered_text = text_area.input_value()
            assert entered_text == test_question, f"Text entry failed. Expected: {test_question}, Got: {entered_text}"
            logger.info(f"✓ Text entered successfully: '{test_question}'")
            
            # Take screenshot with question entered
            self._take_screenshot(page, "message_visibility_03_question_entered")
            
            # Step 4: Click the Send button and immediately check visibility
            logger.info("Step 4: Clicking Send button...")
            
            # Get initial chat content before sending
            chat_content_before = page.locator('body').text_content()
            
            # Click send button
            send_button = page.locator(web_user_page.SEND_BUTTON)
            send_button.click()
            
            # Step 5: IMMEDIATELY observe chat area (no wait) to check message visibility
            logger.info("Step 5: Checking immediate message visibility...")
            
            # Take screenshot immediately after clicking send
            page.wait_for_timeout(500)  # Very short wait just for DOM update
            self._take_screenshot(page, "message_visibility_04_immediately_after_send")
            
            # Check if user message is immediately visible
            page.wait_for_timeout(1000)  # Short wait for message to appear
            chat_content_after = page.locator('body').text_content()
            
            # Verify the sent message appears in chat
            message_visible = test_question in chat_content_after
            assert message_visible, f"User message '{test_question}' is not immediately visible in chat after sending"
            logger.info("✓ User message is immediately visible after sending")
            
            # Take screenshot showing message is visible
            self._take_screenshot(page, "message_visibility_05_message_visible")
            
            # Additional check: Verify the input area is cleared
            current_input_value = text_area.input_value()
            input_cleared = current_input_value == "" or current_input_value.strip() == ""
            assert input_cleared, f"Input area should be cleared after sending. Current value: '{current_input_value}'"
            logger.info("✓ Input area cleared after sending message")
            
            # Wait a bit more and verify message is still visible (not hidden)
            page.wait_for_timeout(3000)
            chat_content_final = page.locator('body').text_content()
            message_still_visible = test_question in chat_content_final
            assert message_still_visible, f"User message '{test_question}' disappeared from chat - should remain visible"
            logger.info("✓ User message remains visible (not hidden after sending)")
            
            # Take final screenshot
            self._take_screenshot(page, "message_visibility_06_final_state")
            
            logger.info("🎉 Chat Message Visibility test completed successfully - Message visible immediately!")
            
        except Exception as e:
            # Take screenshot on any failure
            self._take_screenshot(page, f"message_visibility_FAILURE_{datetime.now().strftime('%H%M%S')}")
            logger.error(f"Chat Message Visibility test failed: {str(e)}")
            raise e

    def test_individual_paint_recommendations(self, page):
        """
        Additional test to specifically validate paint recommendation responses
        """
        web_user_page = WebUserPage(page)
        
        # Navigate to the application
        page.goto(WEB_URL)
        page.wait_for_load_state("domcontentloaded")
        
        # Open chat
        web_user_page.open_chat_window()
        
        # Test specific paint names mentioned in requirements
        paint_keywords = ["Cloud Drift", "Verdant Haze", "Seafoam Light", "Obsidian Pearl"]
        
        question = "I'm looking for a cool, blue-toned paint that feels calm but not gray"
        response, contains_expected, found_keyword = web_user_page.ask_question_and_verify(
            question, paint_keywords
        )
        
        # Log the full response for debugging
        logger.info(f"Paint recommendation response: {response}")
        
        # Check for specific paint names or general blue paint responses
        assert contains_expected or any(keyword.lower() in response.lower() for keyword in ["blue", "teal", "paint", "$59.50"]), \
            f"Response should contain paint recommendations. Response: {response}"

    @pytest.mark.test_id("28935")
    def test_new_session_clears_previous_data(self, page):
        """
        Test ID: 28935
        Test Name: BUG 28572-BYOCC - Customer Chatbot - New Session Should Not Show Previous Session Data
        Description: Validate that clicking "New Session" clears previous chat data and shows clean interface
        
        Test Steps:
        1. Open the Chat Panel
        2. Ask one or more questions in the chat panel
        3. Click on New Session (+)
        4. Verify that previous session data is not visible
        5. Verify clear screen with welcome message is shown
        """
        web_user_page = WebUserPage(page)
        
        # Navigate to the application
        page.goto(WEB_URL)
        page.wait_for_load_state("domcontentloaded")
        logger.info(f"Navigated to URL: {WEB_URL}")
        
        # Take initial screenshot
        self._take_screenshot(page, "new_session_01_initial")
        
        try:
            # Step 1: Open chat window
            logger.info("Step 1: Opening chat panel...")
            web_user_page.open_chat_window()
            
            # Take screenshot after opening chat
            self._take_screenshot(page, "new_session_02_chat_opened")
            
            # Step 2: Ask one or more questions to populate chat history
            logger.info("Step 2: Asking questions to populate chat history...")
            
            # First question
            first_question = "What blue paint colors do you have?"
            web_user_page.enter_a_question(first_question)
            web_user_page.click_send_button()
            web_user_page.wait_for_response(timeout=30000)
            
            # Verify first question and response are visible
            page_content = page.locator('body').text_content()
            assert first_question in page_content, f"First question should be visible in chat history"
            logger.info("✓ First question and response added to chat history")
            
            # Second question to ensure we have multiple messages
            second_question = "Do you offer color matching?"
            web_user_page.enter_a_question(second_question)
            web_user_page.click_send_button()
            web_user_page.wait_for_response(timeout=30000)
            
            # Verify both questions are visible
            page_content = page.locator('body').text_content()
            assert first_question in page_content, f"First question should still be visible"
            assert second_question in page_content, f"Second question should be visible"
            logger.info("✓ Multiple questions and responses are visible in chat history")
            
            # Take screenshot with populated chat
            self._take_screenshot(page, "new_session_03_chat_populated")
            
            # Step 3: Click on New Session (+) button
            logger.info("Step 3: Clicking New Session (+) button...")
            
            # Find and click the New Session button using the provided selector
            new_session_button = page.locator('button[data-slot="button"][title="Start new chat"]')
            assert new_session_button.is_visible(), "New Session button should be visible"
            
            new_session_button.click()
            
            # Wait for the session to reset
            page.wait_for_timeout(3000)
            
            # Take screenshot after clicking new session
            self._take_screenshot(page, "new_session_04_after_new_session")
            
            # Step 4: Verify that previous session data is not visible
            logger.info("Step 4: Verifying previous session data is cleared...")
            
            page_content_after = page.locator('body').text_content()
            
            # Check that previous questions are no longer visible
            assert first_question not in page_content_after, f"First question should not be visible after new session. Found in: {page_content_after[:500]}..."
            assert second_question not in page_content_after, f"Second question should not be visible after new session. Found in: {page_content_after[:500]}..."
            logger.info("✓ Previous session questions are no longer visible")
            
            # Step 5: Verify clear screen with welcome message is shown
            logger.info("Step 5: Verifying clean welcome screen is displayed...")
            
            # Check for expected welcome screen elements
            welcome_elements = [
                "Hey! I'm here to help",
                "Ask me about returns & exchanges, warranties, or general product advice",
                "Click the plus icon to start a new chat anytime"
            ]
            
            for element_text in welcome_elements:
                assert element_text in page_content_after, f"Welcome element '{element_text}' should be visible after new session"
            
            # Verify the AI assistant icon is present
            ai_icon = page.locator('img[alt="AI Assistant"]')
            assert ai_icon.is_visible(), "AI Assistant icon should be visible on welcome screen"
            
            # Verify the welcome container structure
            welcome_container = page.locator('div.flex.flex-col.items-center.justify-center.text-center.space-y-6')
            assert welcome_container.is_visible(), "Welcome container should be visible"
            
            logger.info("✓ Clean welcome screen with all expected elements is displayed")
            
            # Take final screenshot
            self._take_screenshot(page, "new_session_05_clean_screen")
            
            logger.info("🎉 New Session test completed successfully - Previous data cleared and clean screen displayed!")
            
        except Exception as e:
            # Take screenshot on failure
            self._take_screenshot(page, f"new_session_FAILURE_{datetime.now().strftime('%H%M%S')}")
            logger.error(f"New Session test failed: {str(e)}")
            raise e


