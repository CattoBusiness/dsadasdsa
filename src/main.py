import sys, os
from output import Output
from thread_lock import lock
from threading import Thread
from counter import counter
from roblox import Roblox
from util import Util

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    os.mkdir("output")
except:
    pass

try:
    os.mkdir("output/payment_info")
except:
    pass

try:
    os.mkdir("output/pending")
except:
    pass

try:
    os.mkdir("output/premium")
except:
    pass

try:
    os.mkdir("output/rap")
except:
    pass

try:
    os.mkdir("output/robux")
except:
    pass

try:
    os.mkdir("output/summary")
except:
    pass

threading_lock = lock

config = Util.get_config()

THREAD_AMOUNT = config["threads"]
SOLVER_MODE = config.get("solverMode", "RoSolve")
ENABLE_RETRIES = config.get("enableRetries", True)
ACCOUNTS = Util.get_accounts()

# Global lists to track retry-eligible accounts
failed_accounts_for_retry = []
retry_lock = threading_lock

def process_accounts(accounts_list, attempt_number=1):
    """Process a list of accounts with the specified attempt number"""
    global failed_accounts_for_retry
    
    # Reset the counter for each processing round
    counter._counter = 0
    
    # Clear failed accounts list for new attempt
    if attempt_number == 1:
        failed_accounts_for_retry = []
    
    threads = []
    
    if len(accounts_list) <= THREAD_AMOUNT:
        for _ in range(len(accounts_list)):
            thread = Thread(target=Roblox(threading_lock, counter, accounts_list, attempt_number, failed_accounts_for_retry, retry_lock).check)
            thread.start()
            threads.append(thread)
    else:
        for _ in range(THREAD_AMOUNT):
            thread = Thread(target=Roblox(threading_lock, counter, accounts_list, attempt_number, failed_accounts_for_retry, retry_lock).check)
            thread.start()
            threads.append(thread)

    for thread in threads:
        thread.join()

def main() -> None:
    # Display solver mode at startup
    Output("INFO").log(f"Using solver mode: {SOLVER_MODE}")
    if config.get("debugMode", False):
        Output("INFO").log("Debug mode: ENABLED - Detailed API responses will be shown")
    if ENABLE_RETRIES:
        Output("INFO").log("Retries: ENABLED - Failed accounts will be retried up to 2 times")
    else:
        Output("INFO").log("Retries: DISABLED")
    Output("INFO").log(f"Starting checker with {THREAD_AMOUNT} threads for {len(ACCOUNTS)} accounts")
    
    if not ENABLE_RETRIES:
        # Original behavior - no retries
        Output("INFO").log("=== PROCESSING ALL ACCOUNTS (NO RETRIES) ===")
        process_accounts(ACCOUNTS, attempt_number=1)
        Output("SUCCESS").log("Finished checking all accounts")
        return
    
    # Retry behavior - process accounts with retries
    # First attempt - process all accounts
    Output("INFO").log("=== STARTING INITIAL ATTEMPT ===")
    process_accounts(ACCOUNTS, attempt_number=1)
    Output("SUCCESS").log(f"Initial attempt completed. {len(failed_accounts_for_retry)} accounts eligible for retry")
    
    # Retry attempts
    for retry_attempt in range(2):  # 2 additional retry attempts
        if not failed_accounts_for_retry:
            Output("INFO").log("No accounts to retry")
            break
            
        retry_accounts = failed_accounts_for_retry.copy()
        Output("INFO").log(f"=== STARTING RETRY ATTEMPT {retry_attempt + 1}/2 ===")
        Output("INFO").log(f"Retrying {len(retry_accounts)} accounts")
        
        process_accounts(retry_accounts, attempt_number=retry_attempt + 2)
        
        Output("SUCCESS").log(f"Retry attempt {retry_attempt + 1} completed. {len(failed_accounts_for_retry)} accounts still need retry")

    # Final summary
    total_processed = len(ACCOUNTS)
    final_failed = len(failed_accounts_for_retry)
    successful = total_processed - final_failed
    
    Output("SUCCESS").log("=== FINAL RESULTS ===")
    Output("SUCCESS").log(f"Total accounts processed: {total_processed}")
    Output("SUCCESS").log(f"Successful accounts: {successful}")
    Output("SUCCESS").log(f"Failed after all retries: {final_failed}")
    Output("SUCCESS").log("Finished checking all accounts with retries")

if __name__ == "__main__":
    main()
