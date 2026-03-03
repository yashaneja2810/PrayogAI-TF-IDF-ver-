"""
Web Scraper Service
───────────────────
Crawls a website, extracts clean text from every reachable page,
and returns structured chunks ready for embedding.

Strategy:
  1. Try fast HTTP crawl (aiohttp + BeautifulSoup) — follows all internal links
  2. If the root page has too little visible content (JS-rendered SPA),
     switch entirely to Selenium-based crawling with headless Chrome.
"""

import asyncio
import logging
import re
import time
from typing import List, Dict, Set, Optional
from urllib.parse import urljoin, urlparse, urldefrag

import aiohttp
from bs4 import BeautifulSoup

from ..utils.document_processor import DocumentProcessor

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────
MAX_PAGES = 100             # crawl up to 100 pages
CONCURRENCY = 8             # parallel HTTP requests
REQUEST_TIMEOUT = 20        # seconds per HTTP page
SELENIUM_PAGE_WAIT = 6      # seconds to wait for JS rendering
SELENIUM_MAX_PAGES = 50     # cap for slower Selenium crawl
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
STRIP_TAGS = [
    "script", "style", "noscript", "iframe", "svg",
]
# Tags to strip ONLY for body text (keep them for link discovery)
NOISE_TAGS = ["nav", "footer", "header", "aside", "form", "button"]
MIN_CONTENT_LEN = 100
# ──────────────────────────────────────────────────────────────


class WebScraperService:
    """Crawl a website and extract structured text chunks."""

    def __init__(self):
        self.doc_processor = DocumentProcessor(chunk_size=1000, chunk_overlap=200)

    # ══════════════════════════════════════════════════════════
    #  PUBLIC API
    # ══════════════════════════════════════════════════════════

    async def scrape_website(
        self,
        root_url: str,
        login_url: str = None,
        login_username: str = None,
        login_password: str = None,
        login_role: str = None,
    ) -> Dict:
        root_url = self._normalise_url(root_url)
        domain = urlparse(root_url).netloc
        if not domain:
            raise ValueError(f"Invalid URL: {root_url}")

        has_credentials = bool(login_url and login_username and login_password)

        if has_credentials:
            # Authenticated sites always need Selenium (cookies don't transfer to aiohttp)
            logger.info(f"Starting AUTHENTICATED crawl: {root_url}  (domain={domain})")
            page_results = await self._selenium_crawl(
                root_url, domain,
                login_url=login_url,
                login_username=login_username,
                login_password=login_password,
                login_role=login_role,
            )
        else:
            logger.info(f"Starting crawl: {root_url}  (domain={domain}, max={MAX_PAGES})")
            # Phase 1: fast HTTP crawl
            page_results = await self._http_crawl(root_url, domain)
            # Phase 2: if HTTP got nothing, fallback to Selenium
            if not page_results:
                logger.warning("HTTP crawl found no content — switching to Selenium")
                page_results = await self._selenium_crawl(root_url, domain)

        if not page_results:
            raise ValueError(
                f"Could not extract any content from {root_url}. "
                "The site may be blocking bots or have no textual content."
            )

        # Chunk all page texts
        all_chunks: List[str] = []
        all_metadata: List[Dict] = []

        for page in page_results:
            chunks = self.doc_processor.process_text(page["text"])
            for chunk in chunks:
                all_chunks.append(chunk)
                all_metadata.append({
                    "source_url": page["url"],
                    "page_title": page["title"],
                    "source_type": "website",
                })

        logger.info(f"Crawl complete: {len(page_results)} pages → {len(all_chunks)} chunks")

        return {
            "chunks": all_chunks,
            "metadata": all_metadata,
            "pages_scraped": len(page_results),
            "total_chunks": len(all_chunks),
        }

    # ══════════════════════════════════════════════════════════
    #  HTTP CRAWL (fast, for server-rendered sites)
    # ══════════════════════════════════════════════════════════

    async def _http_crawl(self, root_url: str, domain: str) -> List[Dict]:
        visited: Set[str] = set()
        to_visit: List[str] = [root_url]
        page_results: List[Dict] = []

        connector = aiohttp.TCPConnector(limit=CONCURRENCY, ssl=False)
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        ) as session:
            while to_visit and len(visited) < MAX_PAGES:
                batch = []
                while to_visit and len(batch) < CONCURRENCY and len(visited) + len(batch) < MAX_PAGES:
                    url = to_visit.pop(0)
                    url_clean = self._normalise_url(url)
                    if url_clean not in visited:
                        visited.add(url_clean)
                        batch.append(url_clean)

                if not batch:
                    break

                tasks = [self._fetch_page(session, url) for url in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(batch, results):
                    if isinstance(result, Exception):
                        logger.warning(f"  ✗ Failed: {url}: {result}")
                        continue

                    html, final_url = result
                    if not html:
                        continue

                    page_data = self._extract_page_data(html, final_url)
                    if page_data["text"]:
                        page_results.append(page_data)
                        logger.info(
                            f"  ✓ {final_url}  ({len(page_data['text'])} chars, "
                            f"{len(page_data.get('links', []))} links)"
                        )

                    # Follow all discovered internal links
                    for link in page_data.get("links", []):
                        link_clean = self._normalise_url(link)
                        link_domain = urlparse(link_clean).netloc
                        if link_domain == domain and link_clean not in visited:
                            to_visit.append(link_clean)

        logger.info(f"HTTP crawl done: visited {len(visited)} URLs, got {len(page_results)} pages with content")
        return page_results

    async def _fetch_page(self, session: aiohttp.ClientSession, url: str):
        try:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return None, url
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return None, url
                html = await resp.text(errors="replace")
                return html, str(resp.url)
        except Exception as e:
            raise RuntimeError(f"HTTP error for {url}: {e}")

    # ══════════════════════════════════════════════════════════
    #  SELENIUM CRAWL (for JS-rendered SPAs)
    # ══════════════════════════════════════════════════════════

    async def _selenium_crawl(
        self, root_url: str, domain: str,
        login_url: str = None, login_username: str = None, login_password: str = None,
        login_role: str = None,
    ) -> List[Dict]:
        """Full multi-page crawl using headless Chrome."""
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, self._selenium_crawl_sync,
                root_url, domain, login_url, login_username, login_password, login_role,
            )
            return results or []
        except Exception as e:
            logger.error(f"Selenium crawl failed: {e}")
            return []

    def _selenium_crawl_sync(
        self, root_url: str, domain: str,
        login_url: str = None, login_username: str = None, login_password: str = None,
        login_role: str = None,
    ) -> List[Dict]:
        """Synchronous Selenium crawl (runs in thread pool)."""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By

        logger.info(f"Selenium: starting headless Chrome crawl for {root_url}")

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"--user-agent={USER_AGENT}")

        driver = None
        page_results: List[Dict] = []
        visited: Set[str] = set()
        to_visit: List[str] = [root_url]

        try:
            # Selenium 4+ handles ChromeDriver automatically
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(60)
            logger.info("Selenium: Chrome launched successfully")

            # ── Login if credentials provided ──
            if login_url and login_username and login_password:
                login_ok = self._selenium_login(
                    driver, login_url, login_username, login_password, login_role
                )
                if not login_ok:
                    logger.warning("Login may have failed — continuing crawl anyway")

            while to_visit and len(visited) < SELENIUM_MAX_PAGES:
                url = to_visit.pop(0)
                url_clean = self._normalise_url(url)

                if url_clean in visited:
                    continue
                visited.add(url_clean)

                try:
                    driver.get(url_clean)
                    time.sleep(SELENIUM_PAGE_WAIT)  # wait for JS to render

                    html = driver.page_source
                    title = driver.title or url_clean

                    # Try structured extraction first
                    page_data = self._extract_page_data(html, url_clean)

                    # If structured extraction fails, grab all visible text
                    if not page_data["text"]:
                        try:
                            body_text = driver.find_element(By.TAG_NAME, "body").text
                            if body_text and len(body_text.strip()) > MIN_CONTENT_LEN:
                                page_data = {
                                    "url": url_clean,
                                    "title": title,
                                    "text": f"Page: {title}\nURL: {url_clean}\n\n{body_text}",
                                    "links": [],
                                }
                        except Exception:
                            pass

                    if page_data["text"]:
                        page_results.append(page_data)
                        logger.info(f"  ✓ [Selenium] {url_clean}  ({len(page_data['text'])} chars)")

                    # Discover links from the rendered page
                    try:
                        link_elements = driver.find_elements(By.TAG_NAME, "a")
                        for el in link_elements:
                            href = el.get_attribute("href")
                            if href:
                                abs_url, _ = urldefrag(href)
                                parsed = urlparse(abs_url)
                                if (parsed.netloc == domain
                                    and parsed.scheme in ("http", "https")
                                    and self._normalise_url(abs_url) not in visited):
                                    skip_exts = (".pdf", ".png", ".jpg", ".jpeg", ".gif",
                                                 ".svg", ".css", ".js", ".zip", ".mp4", ".mp3")
                                    if not any(parsed.path.lower().endswith(ext) for ext in skip_exts):
                                        to_visit.append(abs_url)
                    except Exception as e:
                        logger.warning(f"  Link discovery failed on {url_clean}: {e}")

                except Exception as e:
                    logger.warning(f"  ✗ [Selenium] Failed: {url_clean}: {e}")
                    continue

            logger.info(f"Selenium crawl done: visited {len(visited)} URLs, got {len(page_results)} pages")
            return page_results

        except Exception as e:
            logger.error(f"Selenium setup failed: {e}")
            return page_results
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    # ══════════════════════════════════════════════════════════
    #  SELENIUM LOGIN
    # ══════════════════════════════════════════════════════════

    def _selenium_login(
        self, driver, login_url: str, username: str, password: str, role: str = None
    ) -> bool:
        """
        Attempt to log in using multiple strategies to handle diverse login forms:
        - Standard single-page login (email + password visible together)
        - Multi-step login (email first → next button → password screen)
        - Role-based login pages (click role card first, then login)
        - Login modals and overlay forms
        - Cookie consent popups that block the form

        Credentials are used ONLY in-memory for this browser session
        and are NEVER logged, stored, or transmitted to our servers.
        """
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        logger.info("Selenium: navigating to login page (credentials NOT logged)")

        try:
            driver.get(login_url)
            time.sleep(4)  # extra wait for heavy pages like VTOP

            # ── Step 0: Dismiss cookie banners / overlays ────────
            self._dismiss_popups(driver)

            # ── Step 0.5: Click role card/tab if specified ────────
            if role:
                self._click_role_card(driver, role)
                time.sleep(3)  # wait for login form to appear after role selection

            # ── Step 1: Try standard login (both fields visible) ─
            success = self._try_standard_login(driver, username, password)
            if success:
                return True

            # ── Step 2: Try multi-step login (email → next → password)
            logger.info("Selenium: trying multi-step login flow")
            driver.get(login_url)
            time.sleep(4)
            self._dismiss_popups(driver)
            if role:
                self._click_role_card(driver, role)
                time.sleep(3)
            success = self._try_multistep_login(driver, username, password)
            if success:
                return True

            logger.warning("Selenium: all login strategies exhausted — login may have failed")
            return False

        except Exception as e:
            logger.error(f"Selenium login error: {e}")
            return False

    def _dismiss_popups(self, driver) -> None:
        """Try to dismiss cookie banners, overlays, and popups that block forms."""
        from selenium.webdriver.common.by import By

        dismiss_selectors = [
            # Cookie consent buttons
            'button[id*="accept"]', 'button[id*="cookie"]', 'button[id*="consent"]',
            'a[id*="accept"]', '[class*="cookie"] button', '[class*="consent"] button',
            'button[aria-label*="accept"]', 'button[aria-label*="Accept"]',
            'button[aria-label*="close"]', 'button[aria-label*="Close"]',
            # Generic close/dismiss
            '[class*="modal"] button[class*="close"]',
            '[class*="overlay"] button[class*="close"]',
            '[class*="popup"] button[class*="close"]',
            'button[class*="dismiss"]',
        ]
        for sel in dismiss_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in buttons:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
                        break
            except Exception:
                continue

    def _click_role_card(self, driver, role: str) -> bool:
        """
        Find and click a role card/tab on the login page.
        Handles patterns like VTOP where you select Student/Employee/Parent/Alumni
        before the login form appears.
        """
        from selenium.webdriver.common.by import By

        role_lower = role.strip().lower()
        logger.info(f"Selenium: looking for role card matching '{role}'")

        # All clickable element types to search
        clickable_selectors = [
            "a", "button", "div[onclick]", "span[onclick]",
            "div[role='button']", "div[role='tab']", "div[role='link']",
            "li[onclick]", "label", "td[onclick]",
            # Generic clickable containers (cards, panels)
            "div.card", "div.panel", "div.tile", "div.option",
            "div[class*='role']", "div[class*='card']", "div[class*='user-type']",
            "div[class*='login-type']", "div[class*='category']",
            # Images with text labels inside clickable parents
            "figure", "a > div",
        ]

        # Strategy 1: Find by exact/partial text match on clickable elements
        for sel in clickable_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    if not el.is_displayed():
                        continue
                    el_text = el.text.strip().lower()
                    # Match role text (exact or contained)
                    if role_lower == el_text or role_lower in el_text:
                        logger.info(f"Selenium: clicking role card: '{el.text.strip()}'")
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                        time.sleep(0.3)
                        el.click()
                        return True
            except Exception:
                continue

        # Strategy 2: Find by aria-label or title attribute
        try:
            all_elements = driver.find_elements(By.CSS_SELECTOR, "[aria-label], [title]")
            for el in all_elements:
                if not el.is_displayed():
                    continue
                aria = (el.get_attribute("aria-label") or "").lower()
                title = (el.get_attribute("title") or "").lower()
                if role_lower in aria or role_lower in title:
                    logger.info(f"Selenium: clicking role element via aria/title: '{role}'")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                    time.sleep(0.3)
                    el.click()
                    return True
        except Exception:
            pass

        # Strategy 3: XPath text search as last resort
        try:
            xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{role_lower}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if el.is_displayed() and el.tag_name in ['a', 'button', 'div', 'span', 'li', 'td', 'label', 'p']:
                    logger.info(f"Selenium: clicking role element via XPath: '{el.text.strip()}'")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                    time.sleep(0.3)
                    el.click()
                    return True
        except Exception:
            pass

        logger.warning(f"Selenium: could not find role card for '{role}'")
        return False

    def _find_visible_field(self, driver, selectors: list):
        """Find the first visible field matching any of the selectors."""
        from selenium.webdriver.common.by import By

        for sel in selectors:
            try:
                fields = driver.find_elements(By.CSS_SELECTOR, sel)
                for field in fields:
                    if field.is_displayed() and field.is_enabled():
                        return field
            except Exception:
                continue
        return None

    def _try_standard_login(self, driver, username: str, password: str) -> bool:
        """Standard login: both username and password fields visible on the same page."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        # Broad selectors for username/email
        username_selectors = [
            'input[type="email"]',
            'input[name="email"]', 'input[name="Email"]',
            'input[name="username"]', 'input[name="Username"]',
            'input[name="user"]', 'input[name="login"]',
            'input[name="userid"]', 'input[name="userId"]',
            'input[name="user_name"]', 'input[name="loginId"]',
            'input[id="email"]', 'input[id="Email"]',
            'input[id="username"]', 'input[id="Username"]',
            'input[id="login-email"]', 'input[id="loginEmail"]',
            'input[id="userid"]', 'input[id="user"]',
            'input[autocomplete="email"]', 'input[autocomplete="username"]',
            'input[placeholder*="email" i]', 'input[placeholder*="Email" i]',
            'input[placeholder*="username" i]', 'input[placeholder*="Username" i]',
            'input[placeholder*="user" i]', 'input[placeholder*="login" i]',
            'input[aria-label*="email" i]', 'input[aria-label*="username" i]',
            'input[type="text"]',  # last resort
        ]

        # Broad selectors for password
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]', 'input[name="Password"]',
            'input[name="pass"]', 'input[name="passwd"]',
            'input[name="user_password"]', 'input[name="loginPassword"]',
            'input[id="password"]', 'input[id="Password"]',
            'input[id="pass"]', 'input[id="loginPassword"]',
            'input[autocomplete="current-password"]',
            'input[placeholder*="password" i]', 'input[placeholder*="Password" i]',
            'input[aria-label*="password" i]',
        ]

        username_field = self._find_visible_field(driver, username_selectors)
        password_field = self._find_visible_field(driver, password_selectors)

        if not username_field:
            logger.info("Selenium: no username field found on page")
            return False

        if not password_field:
            logger.info("Selenium: no password field found — might be multi-step")
            return False

        logger.info("Selenium: found both login fields — attempting standard login")

        # Fill username
        username_field.click()
        time.sleep(0.3)
        username_field.clear()
        username_field.send_keys(username)
        time.sleep(0.5)

        # Fill password
        password_field.click()
        time.sleep(0.3)
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(0.5)

        # Submit
        return self._submit_and_verify(driver, password_field)

    def _try_multistep_login(self, driver, username: str, password: str) -> bool:
        """Multi-step login: email first → next/continue → password screen."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        # Step 1: Find and fill the email/username field
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]', 'input[name="username"]',
            'input[name="identifier"]', 'input[name="login"]',
            'input[id="email"]', 'input[id="username"]',
            'input[id="identifier"]', 'input[id="loginId"]',
            'input[autocomplete="email"]', 'input[autocomplete="username"]',
            'input[placeholder*="email" i]', 'input[placeholder*="username" i]',
            'input[type="text"]',
        ]

        email_field = self._find_visible_field(driver, email_selectors)
        if not email_field:
            return False

        email_field.click()
        time.sleep(0.3)
        email_field.clear()
        email_field.send_keys(username)
        time.sleep(0.5)

        # Step 2: Click "Next" / "Continue" button
        next_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button[id*="next" i]', 'button[id*="continue" i]',
            'button[class*="next" i]', 'button[class*="continue" i]',
            'button[aria-label*="next" i]', 'button[aria-label*="continue" i]',
            'a[id*="next" i]', 'a[class*="next" i]',
            # Buttons with text containing Next/Continue/Sign in
            'button',
        ]

        clicked_next = False
        for sel in next_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        text = btn.text.lower().strip()
                        # For generic 'button' selector, check text content
                        if sel == 'button':
                            if any(kw in text for kw in ['next', 'continue', 'proceed', 'sign in', 'log in', 'submit']):
                                btn.click()
                                clicked_next = True
                                break
                        else:
                            btn.click()
                            clicked_next = True
                            break
                if clicked_next:
                    break
            except Exception:
                continue

        if not clicked_next:
            # Try pressing Enter as fallback
            email_field.send_keys(Keys.RETURN)

        # Wait for password screen to load
        time.sleep(3)

        # Step 3: Find and fill password field
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]', 'input[name="pass"]',
            'input[id="password"]', 'input[id="pass"]',
            'input[autocomplete="current-password"]',
            'input[placeholder*="password" i]',
        ]

        password_field = self._find_visible_field(driver, password_selectors)
        if not password_field:
            logger.warning("Selenium: password field not found after multi-step navigation")
            return False

        logger.info("Selenium: found password field on second step — completing login")

        password_field.click()
        time.sleep(0.3)
        password_field.clear()
        password_field.send_keys(password)
        time.sleep(0.5)

        return self._submit_and_verify(driver, password_field)

    def _submit_and_verify(self, driver, last_field) -> bool:
        """Submit the form and check if login succeeded."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys

        pre_url = driver.current_url

        # Try clicking submit button
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button[id*="login" i]', 'button[id*="signin" i]',
            'button[id*="sign-in" i]', 'button[id*="submit" i]',
            'button[class*="login" i]', 'button[class*="signin" i]',
            'button[class*="submit" i]',
            'button[aria-label*="sign in" i]', 'button[aria-label*="log in" i]',
            'a[class*="login" i]', 'a[class*="submit" i]',
        ]

        # Also try buttons by their visible text
        text_buttons = [
            'button', 'a[role="button"]', 'div[role="button"]', 'span[role="button"]',
        ]

        submitted = False

        # First: specific selectors
        for sel in submit_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, sel)
                for btn in buttons:
                    if btn.is_displayed() and btn.is_enabled():
                        btn.click()
                        submitted = True
                        break
                if submitted:
                    break
            except Exception:
                continue

        # Second: find by text content
        if not submitted:
            for sel in text_buttons:
                try:
                    buttons = driver.find_elements(By.CSS_SELECTOR, sel)
                    for btn in buttons:
                        if btn.is_displayed() and btn.is_enabled():
                            text = btn.text.lower().strip()
                            if any(kw in text for kw in ['log in', 'login', 'sign in', 'signin', 'submit', 'enter']):
                                btn.click()
                                submitted = True
                                break
                    if submitted:
                        break
                except Exception:
                    continue

        # Last resort: press Enter
        if not submitted:
            last_field.send_keys(Keys.RETURN)

        # Verify login
        time.sleep(5)

        post_url = driver.current_url
        page_text = ""
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception:
            pass

        # Check for success indicators
        login_failed_indicators = [
            "invalid", "incorrect", "wrong password", "try again",
            "failed", "error", "not found", "doesn't match",
            "invalid credentials", "authentication failed",
        ]

        if post_url != pre_url:
            logger.info(f"Selenium: login appears successful (redirected to {post_url})")
            return True

        # Check if page shows error messages
        for indicator in login_failed_indicators:
            if indicator in page_text:
                logger.warning(f"Selenium: login likely failed — page contains '{indicator}'")
                return False

        # URL didn't change but no error messages — might be SPA, still try
        logger.info("Selenium: URL unchanged but no error detected — proceeding with crawl")
        return True

    # ══════════════════════════════════════════════════════════
    #  CONTENT EXTRACTION
    # ══════════════════════════════════════════════════════════

    def _extract_page_data(self, html: str, url: str) -> Dict:
        """Parse HTML → clean text + internal links. Handles SPAs with <template> content."""
        soup = BeautifulSoup(html, "html.parser")

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        # 1. Extract text from <template> tags (SPA content)
        template_texts = []
        for tmpl in soup.find_all("template"):
            tmpl_text = tmpl.get_text(separator="\n", strip=True)
            if tmpl_text and len(tmpl_text) > 20:
                template_texts.append(tmpl_text)

        # 2. Extract structured data from inline <script>
        script_data_texts = []
        for script_tag in soup.find_all("script"):
            script_content = script_tag.string or ""
            if not script_content:
                continue
            quoted_strings = re.findall(
                r"(?:title|name|desc|description|brand|cat|category|label|text|content)"
                r"\s*[:=]\s*['\"]([^'\"]{10,})['\"]",
                script_content,
                re.IGNORECASE,
            )
            if quoted_strings:
                script_data_texts.extend(quoted_strings)

        # 3. Extract all links BEFORE removing noise (for link discovery)
        links = self._extract_links(html, url)

        # 4. Remove noise tags
        for tag_name in STRIP_TAGS + NOISE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # 5. Extract visible body text
        main = soup.find("main") or soup.find("article") or soup.find("body")
        body_text = ""
        if main:
            body_text = main.get_text(separator="\n", strip=True)
            body_text = re.sub(r"\n{3,}", "\n\n", body_text)

        # 6. Combine all text sources
        parts = []
        if body_text and len(body_text.strip()) > 20:
            parts.append(body_text)
        if template_texts:
            parts.append("--- Page Sections ---")
            parts.extend(template_texts)
        if script_data_texts:
            parts.append("--- Catalog Data ---")
            parts.extend(script_data_texts)

        combined_text = "\n\n".join(parts)

        if len(combined_text.strip()) < 50:
            return {"url": url, "title": title, "text": "", "links": links}

        structured_text = f"Page: {title}\nURL: {url}\n\n{combined_text}"

        return {
            "url": url,
            "title": title,
            "text": structured_text,
            "links": links,
        }

    def _extract_links(self, html: str, url: str) -> List[str]:
        """Extract all same-domain links from raw HTML."""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        base_domain = urlparse(url).netloc

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            abs_url = urljoin(url, href)
            abs_url, _ = urldefrag(abs_url)
            parsed = urlparse(abs_url)

            if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                skip_exts = (".pdf", ".png", ".jpg", ".jpeg", ".gif", ".svg",
                             ".css", ".js", ".zip", ".mp4", ".mp3")
                if not any(parsed.path.lower().endswith(ext) for ext in skip_exts):
                    links.append(abs_url)

        return list(set(links))

    def _normalise_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        url, _ = urldefrag(url)
        url = url.rstrip("/")
        return url
