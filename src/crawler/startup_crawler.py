import aiohttp
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from bs4 import BeautifulSoup


# ============================================================
# FILES
# ============================================================

INPUT_FILE = "data/raw/startup_urls.json"

OUTPUT_FILE = "data/processed/startups.json"
FAILED_FILE = "data/processed/failed_startups.json"
REJECTED_FILE = "data/processed/rejected_startups.json"


# ============================================================
# SETTINGS
# ============================================================

MAX_CONCURRENT_REQUESTS = 10

BATCH_SIZE = 50

TARGET_STARTUPS = 1000

REQUEST_TIMEOUT = 30


# ============================================================
# HEADERS
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0 Safari/537.36"
    )
}


# ============================================================
# LOAD JSON
# ============================================================

def load_json_file(filename, default):

    if not os.path.exists(filename):
        return default

    try:

        with open(
            filename,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

            if isinstance(data, type(default)):
                return data

    except Exception as error:

        print(
            f"Could not load {filename}: {error}"
        )

    return default


# ============================================================
# SAVE JSON SAFELY
# ============================================================

def save_json_file(filename, data):

    os.makedirs(
        os.path.dirname(filename),
        exist_ok=True
    )

    temporary_file = filename + ".tmp"

    try:

        with open(
            temporary_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4,
                ensure_ascii=False
            )


        # ----------------------------------------------------
        # Windows-safe file replacement
        # ----------------------------------------------------

        for attempt in range(5):

            try:

                os.replace(
                    temporary_file,
                    filename
                )

                return True


            except PermissionError:

                if attempt < 4:

                    import time

                    time.sleep(1)

                else:

                    print(
                        f"[WARNING] Could not replace "
                        f"{filename} after 5 attempts."
                    )

                    print(
                        "[WARNING] Existing checkpoint "
                        "has been preserved."
                    )


    except Exception as error:

        print(
            f"[WARNING] Save failed for "
            f"{filename}: {error}"
        )


    return False


# ============================================================
# TIMESTAMP
# ============================================================

def current_timestamp():

    return (
        datetime.now(timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# EXTRACT COMPANY NAME
# ============================================================

def extract_company_name(soup):

    # --------------------------------------------------------
    # METHOD 1: PAGE TITLE
    # --------------------------------------------------------

    if soup.title:

        title = clean_text(
            soup.title.get_text(
                " ",
                strip=True
            )
        )

        # Example:
        # 10 By 10: description | Y Combinator

        title = re.sub(
            r"\s*\|\s*Y Combinator.*$",
            "",
            title,
            flags=re.I
        )

        title = re.sub(
            r":\s*.*$",
            "",
            title
        )

        if title:

            return title.strip()


    # --------------------------------------------------------
    # METHOD 2: MAIN HEADING
    # --------------------------------------------------------

    heading = soup.find("h1")

    if heading:

        name = clean_text(
            heading.get_text(
                " ",
                strip=True
            )
        )

        if name:

            return name


    return None


# ============================================================
# EXTRACT EMPLOYEE COUNT
# ============================================================

def extract_employee_count(text):

    # --------------------------------------------------------
    # YC currently uses:
    #
    # Team Size: 5
    # --------------------------------------------------------

    patterns = [

        r"Team\s+Size\s*:\s*(\d+)",

        r"Team\s+size\s*(\d+)",

        r"Employees\s*:\s*(\d+)",

        r"Employee\s+Count\s*:\s*(\d+)",

        r"(\d+)\s+employees\b"

    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.I
        )

        if match:

            try:

                count = int(
                    match.group(1)
                )

                if 0 <= count <= 1_000_000:

                    return count

            except ValueError:

                pass


    return None


# ============================================================
# EXTRACT DESCRIPTION
# ============================================================

def extract_description(soup):

    # YC pages generally contain the description
    # in the visible page text.

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    return text


# ============================================================
# VALIDATE YC PAGE
# ============================================================

def validate_startup_page(
    company_name,
    text
):

    if not company_name:

        return False


    if len(company_name) < 2:

        return False


    # YC page indicators

    indicators = [

        "Y Combinator",

        "Batch:",

        "Status:",

        "Location:",

        "Team Size:",

        "Company Jobs",

        "Founder"

    ]


    indicator_count = sum(
        indicator.lower() in text.lower()
        for indicator in indicators
    )


    # Require at least two strong YC indicators.

    if indicator_count < 2:

        return False


    return True


# ============================================================
# CONVERT TO ASSIGNMENT SCHEMA
# ============================================================

def convert_to_schema(
    company_name,
    employee_count,
    source_url
):

    return {

        "schemaVersion": "1.0",

        "recordType": "STARTUP",

        "source": {

            "name": "Y Combinator",

            "url": source_url

        },

        "content": {

            "entityName": company_name,

            "data": {

                "employeeCount": employee_count

            }

        },

        "collectedAt": current_timestamp()

    }


# ============================================================
# SCRAPE ONE PAGE
# ============================================================

async def scrape_page(
    session,
    semaphore,
    url
):

    async with semaphore:

        try:

            async with session.get(
                url,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(
                    total=REQUEST_TIMEOUT
                )
            ) as response:

                if response.status != 200:

                    return {
                        "status": "failed",
                        "url": url,
                        "reason": f"HTTP {response.status}"
                    }


                html = await response.text()

                if not html:

                    return {
                        "status": "failed",
                        "url": url,
                        "reason": "Empty response"
                    }


                soup = BeautifulSoup(
                    html,
                    "html.parser"
                )


                # Remove unnecessary elements

                for element in soup(
                    [
                        "script",
                        "style",
                        "noscript",
                        "svg"
                    ]
                ):

                    element.decompose()


                text = extract_description(
                    soup
                )


                if len(text) < 200:

                    return {
                        "status": "failed",
                        "url": url,
                        "reason": "Insufficient page text"
                    }


                company_name = extract_company_name(
                    soup
                )


                if not validate_startup_page(
                    company_name,
                    text
                ):

                    return {
                        "status": "rejected",
                        "url": url,
                        "reason": "YC startup page validation failed"
                    }


                employee_count = extract_employee_count(
                    text
                )


                record = convert_to_schema(
                    company_name,
                    employee_count,
                    url
                )


                return {
                    "status": "success",
                    "url": url,
                    "record": record
                }


        except asyncio.CancelledError:

            raise


        except Exception as error:

            return {
                "status": "failed",
                "url": url,
                "reason": str(error)
            }


# ============================================================
# NORMALIZE EXISTING RECORD
# ============================================================

def normalize_existing_record(record):

    if not isinstance(record, dict):

        return None


    # --------------------------------------------------------
    # Already canonical
    # --------------------------------------------------------

    if (
        record.get("schemaVersion") == "1.0"
        and record.get("recordType") == "STARTUP"
        and record.get("source")
        and record.get("content")
    ):

        content = record.get(
            "content",
            {}
        )

        name = content.get(
            "entityName"
        )

        data = content.get(
            "data",
            {}
        )

        employee_count = data.get(
            "employeeCount"
        )


        if employee_count is None:

            employee_count = record.get(
                "employeeCount"
            )


        source = record.get(
            "source",
            {}
        )

        source_url = source.get(
            "url"
        )


        if not name or not source_url:

            return None


        return {

            "schemaVersion": "1.0",

            "recordType": "STARTUP",

            "source": {

                "name": "Y Combinator",

                "url": source_url

            },

            "content": {

                "entityName": name,

                "data": {

                    "employeeCount": employee_count

                }

            },

            "collectedAt": record.get(
                "collectedAt",
                current_timestamp()
            )

        }


    # --------------------------------------------------------
    # Old format
    # --------------------------------------------------------

    name = record.get(
        "entityName"
    )

    employee_count = record.get(
        "employeeCount"
    )

    source_url = record.get(
        "sourceUrl"
    )


    if name and source_url:

        return {

            "schemaVersion": "1.0",

            "recordType": "STARTUP",

            "source": {

                "name": "Y Combinator",

                "url": source_url

            },

            "content": {

                "entityName": name,

                "data": {

                    "employeeCount": employee_count

                }

            },

            "collectedAt": current_timestamp()

        }


    return None


# ============================================================
# MAIN
# ============================================================

async def main():

    print("=" * 60)

    print("YC STARTUP CRAWLER")

    print("=" * 60)


    # --------------------------------------------------------
    # Load URLs
    # --------------------------------------------------------

    if not os.path.exists(INPUT_FILE):

        print(
            f"Input file not found: {INPUT_FILE}"
        )

        return


    startup_urls = load_json_file(
        INPUT_FILE,
        []
    )


    startup_urls = sorted(
        set(startup_urls)
    )


    print(
        f"Startup URLs available: {len(startup_urls)}"
    )


    # --------------------------------------------------------
    # Load existing results
    # --------------------------------------------------------

    existing_results = load_json_file(
        OUTPUT_FILE,
        []
    )


    existing_failed = load_json_file(
        FAILED_FILE,
        []
    )


    existing_rejected = load_json_file(
        REJECTED_FILE,
        []
    )


    # --------------------------------------------------------
    # Normalize existing records
    # --------------------------------------------------------

    results = []

    seen_urls = set()

    seen_names = set()


    for old_record in existing_results:

        record = normalize_existing_record(
            old_record
        )

        if not record:

            continue


        url = record[
            "source"
        ][
            "url"
        ]


        name = record[
            "content"
        ][
            "entityName"
        ]


        normalized_name = clean_text(
            name
        ).lower()


        if url in seen_urls:

            continue


        if normalized_name in seen_names:

            continue


        results.append(
            record
        )

        seen_urls.add(
            url
        )

        seen_names.add(
            normalized_name
        )


    print(
        f"Existing valid startups: {len(results)}"
    )


    # --------------------------------------------------------
    # Processed URLs
    # --------------------------------------------------------

    rejected_urls = sorted(
        set(existing_rejected)
    )


    failed_urls = sorted(
        set(existing_failed)
    )


    processed_urls = set(
        seen_urls
    )


    processed_urls.update(
        rejected_urls
    )


    # --------------------------------------------------------
    # Remaining URLs
    # --------------------------------------------------------

    remaining_urls = [

        url

        for url in startup_urls

        if url not in processed_urls

    ]


    print(
        f"Remaining URLs: {len(remaining_urls)}"
    )


    # --------------------------------------------------------
    # Stop if target already reached
    # --------------------------------------------------------

    if len(results) >= TARGET_STARTUPS:

        print(
            f"\nTarget of {TARGET_STARTUPS} startups already reached."
        )

        save_json_file(
            OUTPUT_FILE,
            results
        )

        return


    # --------------------------------------------------------
    # SEMAPHORE
    # --------------------------------------------------------

    semaphore = asyncio.Semaphore(
        MAX_CONCURRENT_REQUESTS
    )


    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS
    )


    # --------------------------------------------------------
    # CRAWL
    # --------------------------------------------------------

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:


        total_batches = (
            (
                len(remaining_urls)
                + BATCH_SIZE
                - 1
            )
            // BATCH_SIZE
        )


        for start in range(
            0,
            len(remaining_urls),
            BATCH_SIZE
        ):


            # Stop once target reached.

            if len(results) >= TARGET_STARTUPS:

                print(
                    "\nTARGET REACHED."
                )

                break


            batch = remaining_urls[
                start:start + BATCH_SIZE
            ]


            batch_number = (
                start // BATCH_SIZE
            ) + 1


            print("\n" + "=" * 60)

            print(
                f"Batch {batch_number}/{total_batches}"
            )

            print(
                f"Batch URLs: {len(batch)}"
            )

            print(
                f"Current startups: {len(results)}"
            )

            print("=" * 60)


            tasks = [

                asyncio.create_task(
                    scrape_page(
                        session,
                        semaphore,
                        url
                    )
                )

                for url in batch

            ]


            for task in asyncio.as_completed(
                tasks
            ):

                result = await task


                url = result.get(
                    "url"
                )


                status = result.get(
                    "status"
                )


                # ====================================================
                # SUCCESS
                # ====================================================

                if status == "success":

                    record = result[
                        "record"
                    ]


                    name = record[
                        "content"
                    ][
                        "entityName"
                    ]


                    normalized_name = clean_text(
                        name
                    ).lower()


                    # Deduplicate

                    if (
                        url not in seen_urls
                        and normalized_name not in seen_names
                    ):

                        results.append(
                            record
                        )

                        seen_urls.add(
                            url
                        )

                        seen_names.add(
                            normalized_name
                        )


                        print(
                            f"[SUCCESS] "
                            f"{name}"
                        )


                        save_json_file(
                            OUTPUT_FILE,
                            results
                        )


                # ====================================================
                # REJECTED
                # ====================================================

                elif status == "rejected":

                    rejected_urls.append(
                        url
                    )

                    rejected_urls = sorted(
                        set(rejected_urls)
                    )


                    save_json_file(
                        REJECTED_FILE,
                        rejected_urls
                    )


                # ====================================================
                # FAILED
                # ====================================================

                elif status == "failed":

                    failed_urls.append(
                        url
                    )

                    failed_urls = sorted(
                        set(failed_urls)
                    )


                    save_json_file(
                        FAILED_FILE,
                        failed_urls
                    )


            # --------------------------------------------------------
            # Batch checkpoint
            # --------------------------------------------------------

            save_json_file(
                OUTPUT_FILE,
                results
            )


            save_json_file(
                FAILED_FILE,
                failed_urls
            )


            save_json_file(
                REJECTED_FILE,
                rejected_urls
            )


            print("\nBatch completed.")

            print(
                f"Successful startups: {len(results)}"
            )

            print(
                f"Rejected: {len(rejected_urls)}"
            )

            print(
                f"Failed: {len(failed_urls)}"
            )


    # ------------------------------------------------------------
    # FINAL SAVE
    # ------------------------------------------------------------

    save_json_file(
        OUTPUT_FILE,
        results
    )


    save_json_file(
        FAILED_FILE,
        failed_urls
    )


    save_json_file(
        REJECTED_FILE,
        rejected_urls
    )


    print("\n" + "=" * 60)

    print("STARTUP CRAWLER COMPLETE")

    print("=" * 60)

    print(
        f"Unique startups: {len(results)}"
    )

    print(
        f"Rejected: {len(rejected_urls)}"
    )

    print(
        f"Failed: {len(failed_urls)}"
    )

    print(
        f"Target: {TARGET_STARTUPS}"
    )


    if len(results) >= TARGET_STARTUPS:

        print(
            "\nSUCCESS: Minimum 1,000 startups reached."
        )

    else:

        print(
            "\nTarget not reached yet."
        )

        print(
            "Failed URLs can be retried later."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    asyncio.run(main())
