from util import Util
from time import sleep
from curl_cffi import requests
from output import Output
import asyncio

config = Util.get_config()

SOLVER_KEY = config["solverKey"]
SOLVER_MODE = config.get("solverMode", "RoSolve")  # Default to RoSolve if not specified
DEBUG_MODE = config.get("debugMode", False)  # Debug mode for troubleshooting

# Try to import freecap-client for FreeCap mode
try:
    from freecap import solve_funcaptcha, FunCaptchaPreset, FreeCapAPIException, FreeCapTimeoutException, FreeCapValidationException
    import logging
    FREECAP_AVAILABLE = True
    
    # Aggressively control freecap-client library logging
    def suppress_freecap_logging():
        """Completely suppress all freecap-related logging when debug mode is off"""
        import logging
        
        # Suppress freecap_client and any related loggers
        logger_names = ['freecap_client', 'freecap', 'freecap-client']
        
        for logger_name in logger_names:
            logger = logging.getLogger(logger_name)
            if DEBUG_MODE:
                logger.setLevel(logging.DEBUG)
                logger.propagate = True
                logger.disabled = False
            else:
                logger.setLevel(logging.CRITICAL + 1)
                logger.propagate = False
                logger.disabled = True
                logger.handlers.clear()
                logger.addHandler(logging.NullHandler())
    
    # Apply logging suppression
    suppress_freecap_logging()
        
except ImportError:
    FREECAP_AVAILABLE = False
    if SOLVER_MODE.lower() == "freecap":
        Output("ERROR").log("freecap-client not installed. Run: pip install freecap-client")
        Output("ERROR").log("Falling back to RoSolve mode")

def get_token_rosolve(roblox_session: requests.Session, blob, proxy):
    """Original RoSolve implementation"""
    session = requests.Session()

    challengeInfo = {
        "publicKey": "476068BF-9607-4799-B53D-966BE98E2B81",
        "site": "https://www.roblox.com/",
        "surl": "https://arkoselabs.roblox.com",
        "capiMode": "inline",
        "styleTheme": "default",
        "languageEnabled": False,
        "jsfEnabled": False,
        "extraData": {
            "blob": blob
        },
        "ancestorOrigins": ["https://www.roblox.com"],
        "treeIndex": [1],
        "treeStructure": "[[],[]]",
        "locationHref":  "https://www.roblox.com/arkose/iframe",
        "documentReferrer": "https://www.roblox.com/login"
    }

    browserInfo = {
        'Sec-Ch-Ua': roblox_session.headers["sec-ch-ua"],
        'User-Agent': roblox_session.headers["user-agent"],
        'Mobile': False
    }

    payload = {
        "key": SOLVER_KEY,
        "challengeInfo": challengeInfo,
        "browserInfo": browserInfo,
        "proxy": proxy
    }

    response = session.post("https://rosolve.pro/createTask", json=payload, timeout=120).json()

    task_id = response.get("taskId")

    if task_id == None:
        raise ValueError(f"Failed to get taskId, reason: {response.get('error', 'Unknown error')}")
    
    counter = 0

    while counter < 60:
        sleep(1)

        solution = session.get(f"https://rosolve.pro/taskResult/{task_id}").json()

        if solution["status"] == "completed":
            return solution["result"]["solution"]
        
        elif solution["status"] == "failed":
            return None
        
        counter += 1

    return None

def get_token_freecap(roblox_session: requests.Session, blob, proxy):
    """FreeCap implementation using the official freecap-client library"""
    if not FREECAP_AVAILABLE:
        raise ValueError("freecap-client library not available. Install with: pip install freecap-client")
    
    # Extract chrome version from user agent for FreeCap
    user_agent = roblox_session.headers.get("user-agent", "")
    chrome_version = "138"  # Default
    
    if "Chrome/" in user_agent:
        try:
            detected_version = int(user_agent.split("Chrome/")[1].split(".")[0])
            
            # Map to supported versions (137 and 138)
            if detected_version >= 138:
                chrome_version = "138"
            elif detected_version == 137:
                chrome_version = "137" 
            else:
                # For older versions, use 137
                chrome_version = "137"
                
            if DEBUG_MODE:
                Output("INFO").log(f"Detected Chrome version: {detected_version}, Using: {chrome_version}")
                
        except:
            chrome_version = "138"  # Fallback to 138

    async def solve_captcha_async():
        try:
            # Apply aggressive logging suppression right before solving
            def suppress_freecap_logging():
                """Completely suppress all freecap-related logging"""
                import logging
                logger_names = ['freecap_client', 'freecap', 'freecap-client']
                
                for logger_name in logger_names:
                    logger = logging.getLogger(logger_name)
                    if DEBUG_MODE:
                        logger.setLevel(logging.DEBUG)
                        logger.propagate = True
                        logger.disabled = False
                    else:
                        logger.setLevel(logging.CRITICAL + 1)
                        logger.propagate = False
                        logger.disabled = True
                        logger.handlers.clear()
                        logger.addHandler(logging.NullHandler())
            
            # Suppress logging before solving
            suppress_freecap_logging()
            
            if DEBUG_MODE:
                Output("INFO").log(f"FreeCap solving with preset: ROBLOX_LOGIN, chrome: {chrome_version}, proxy: {proxy}")
            
            # Use the convenience function for FunCaptcha with Roblox preset
            solution = await solve_funcaptcha(
                api_key=SOLVER_KEY,
                preset=FunCaptchaPreset.ROBLOX_LOGIN,
                chrome_version=chrome_version,
                blob=blob if blob else "undefined",
                proxy=proxy
            )
            
            if DEBUG_MODE:
                Output("SUCCESS").log(f"FreeCap solution received: {solution[:50] if solution else 'None'}...")
            
            return solution
            
        except FreeCapAPIException as e:
            error_msg = f"FreeCap API Error: {e}"
            if DEBUG_MODE:
                Output("ERROR").log(error_msg)
            raise ValueError(error_msg)
            
        except FreeCapTimeoutException as e:
            error_msg = f"FreeCap Timeout: {e}"
            if DEBUG_MODE:
                Output("ERROR").log(error_msg)
            raise ValueError(error_msg)
            
        except FreeCapValidationException as e:
            error_msg = f"FreeCap Validation Error: {e}"
            if DEBUG_MODE:
                Output("ERROR").log(error_msg)
            raise ValueError(error_msg)
            
        except Exception as e:
            error_msg = f"FreeCap Unexpected Error: {e}"
            if DEBUG_MODE:
                Output("ERROR").log(error_msg)
            raise ValueError(error_msg)

    # Run the async function in a new event loop
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, create a new one
            import threading
            result_container = {}
            exception_container = {}
            
            def run_in_thread():
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    result_container['result'] = new_loop.run_until_complete(solve_captcha_async())
                    new_loop.close()
                except Exception as e:
                    exception_container['exception'] = e
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
            if 'exception' in exception_container:
                raise exception_container['exception']
            
            return result_container.get('result')
        else:
            # If no loop is running, use the current one
            return loop.run_until_complete(solve_captcha_async())
    except RuntimeError:
        # No event loop exists, create a new one
        return asyncio.run(solve_captcha_async())

def get_token(roblox_session: requests.Session, blob, proxy):
    """Main function that routes to the appropriate solver based on config"""
    if SOLVER_MODE.lower() == "freecap":
        if FREECAP_AVAILABLE:
            return get_token_freecap(roblox_session, blob, proxy)
        else:
            Output("ERROR").log("FreeCap mode selected but freecap-client not installed. Falling back to RoSolve.")
            return get_token_rosolve(roblox_session, blob, proxy)
    else:
        # Default to RoSolve for backwards compatibility
        return get_token_rosolve(roblox_session, blob, proxy)
