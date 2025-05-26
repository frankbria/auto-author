import pytest
import asyncio
import threading
from httpx import AsyncClient, ASGITransport
from app.main import app
from fastapi.encoders import jsonable_encoder
from app.db import base
import pymongo

@pytest.mark.asyncio
async def test_debug_event_loop_state(async_client_factory, test_book):
    """Debug exactly what's happening to the event loop"""

    print(f"\n=== START OF TEST ===")
    print(f"Thread: {threading.current_thread().name}")
    print(f"Thread ID: {threading.get_ident()}")

    try:
        loop = asyncio.get_event_loop()
        print(f"Initial loop: {id(loop)}")
        print(f"Initial loop running: {loop.is_running()}")
        print(f"Initial loop closed: {loop.is_closed()}")
        print(f"Initial tasks: {len(asyncio.all_tasks(loop))}")
    except RuntimeError as e:
        print(f"Can't get initial loop: {e}")

    print(f"\n--- Creating client ---")
    api_client = await async_client_factory()

    try:
        loop = asyncio.get_event_loop()
        print(f"After client creation loop: {id(loop)}")
        print(f"After client creation running: {loop.is_running()}")
        print(f"After client creation closed: {loop.is_closed()}")
        print(f"After client creation tasks: {len(asyncio.all_tasks(loop))}")
    except RuntimeError as e:
        print(f"Can't get loop after client: {e}")

    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)

    print(f"\n--- Making first request ---")
    try:
        response = await api_client.post(f"/api/v1/books/", json=payload_book)
        print(f"First request status: {response.status_code}")

        loop = asyncio.get_event_loop()
        print(f"After first request loop: {id(loop)}")
        print(f"After first request running: {loop.is_running()}")
        print(f"After first request closed: {loop.is_closed()}")
        print(f"After first request tasks: {len(asyncio.all_tasks(loop))}")

    except Exception as e:
        print(f"First request failed: {e}")
        try:
            loop = asyncio.get_event_loop()
            print(f"After failed request loop closed: {loop.is_closed()}")
        except:
            print("Can't even get loop after failure")

    print(f"\n--- Making second request ---")
    try:
        response2 = await api_client.get(f"/api/v1/books/")
        print(f"Second request status: {response2.status_code}")

        loop = asyncio.get_event_loop()
        print(f"After second request loop: {id(loop)}")
        print(f"After second request running: {loop.is_running()}")
        print(f"After second request closed: {loop.is_closed()}")

    except Exception as e:
        print(f"Second request failed: {e}")
        try:
            loop = asyncio.get_event_loop()
            print(f"After failed second request loop closed: {loop.is_closed()}")
        except:
            print("Can't even get loop after second failure")

    print(f"\n--- Closing client ---")
    try:
        await api_client.aclose()
        print("Client closed successfully")

        loop = asyncio.get_event_loop()
        print(f"After client close loop: {id(loop)}")
        print(f"After client close running: {loop.is_running()}")
        print(f"After client close closed: {loop.is_closed()}")
        print(f"After client close tasks: {len(asyncio.all_tasks(loop))}")

    except Exception as e:
        print(f"Client close failed: {e}")

    print(f"=== END OF TEST ===\n")


@pytest.mark.asyncio
async def test_second_test_to_see_loop_state(async_client_factory, test_book):
    """This should fail if the first test corrupted the loop"""

    print(f"\n=== SECOND TEST START ===")
    print(f"Thread: {threading.current_thread().name}")
    print(f"Thread ID: {threading.get_ident()}")

    try:
        loop = asyncio.get_event_loop()
        print(f"Second test initial loop: {id(loop)}")
        print(f"Second test initial running: {loop.is_running()}")
        print(f"Second test initial closed: {loop.is_closed()}")
    except RuntimeError as e:
        print(f"Second test can't get loop: {e}")
        raise

    print("--- Second test creating client ---")
    api_client = await async_client_factory()

    try:
        payload = test_book.copy()
        payload["owner_id"] = str(test_book["owner_id"])
        del payload["_id"]
        del payload["id"]
        del payload["toc_items"]
        del payload["published"]
        payload_book = jsonable_encoder(payload)

        print("--- Second test making request ---")
        response = await api_client.post(f"/api/v1/books/", json=payload_book)
        print(f"Second test request status: {response.status_code}")

    finally:
        await api_client.aclose()
        print("=== SECOND TEST END ===\n")


@pytest.mark.asyncio
async def test_debug_500_error(async_client_factory, test_book):
    """Debug what's causing the 500 error on the second request"""

    api_client = await async_client_factory()

    try:
        payload = test_book.copy()
        payload["owner_id"] = str(test_book["owner_id"])
        del payload["_id"]
        del payload["id"]
        del payload["toc_items"]
        del payload["published"]
        payload_book = jsonable_encoder(payload)

        print(f"\n--- First POST request ---")
        response = await api_client.post(f"/api/v1/books/", json=payload_book)
        print(f"POST status: {response.status_code}")
        if response.status_code != 201:
            print(f"POST error: {response.text}")
        else:
            book_data = response.json()
            print(f"Created book ID: {book_data.get('id')}")

        print(f"\n--- Second GET request ---")
        response = await api_client.get(f"/api/v1/books/")
        print(f"GET status: {response.status_code}")

        if response.status_code != 200:
            print(f"GET error response: {response.text}")
            try:
                error_detail = response.json()
                print(f"GET error detail: {error_detail}")
            except:
                print("Could not parse error as JSON")
        else:
            books = response.json()
            print(f"GET success: Found {len(books)} books")

        # Try a specific book GET to see if that works
        if response.status_code == 201:  # If POST worked
            book_id = response.json()["id"]
            print(f"\n--- Third GET specific book request ---")
            response = await api_client.get(f"/api/v1/books/{book_id}")
            print(f"GET specific book status: {response.status_code}")
            if response.status_code != 200:
                print(f"GET specific book error: {response.text}")

    except Exception as e:
        print(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()

    finally:
        await api_client.aclose()


@pytest.mark.asyncio
async def test_debug_database_state(async_client_factory, test_book):
    """Check if the database state is causing issues"""

    # Check database state before any requests
    from app.db import base

    print(f"\n--- Database state check ---")
    try:
        # switch to a sync PyMongo client so we hit the test DB only
        sync_client = pymongo.MongoClient("mongodb://localhost:27017/auto-author")
        sync_db = sync_client.get_database()
        sync_books = sync_db.get_collection("books")
        sync_users = sync_db.get_collection("users")

        books_in_db = list(sync_books.find({}))
        print(f"Books in DB before test: {len(books_in_db)}")
        users_in_db = list(sync_users.find({}))
        print(f"Users in DB before test: {len(users_in_db)}")

    except Exception as e:
        print(f"Database query error: {e}")

    api_client = await async_client_factory()

    try:
        # Simple GET without any prior POST
        print(f"\n--- Direct GET request (no POST first) ---")
        response = await api_client.get(f"/api/v1/books/")
        print(f"Direct GET status: {response.status_code}")

        if response.status_code == 500:
            print(f"Direct GET error: {response.text}")
        else:
            books = response.json()
            print(f"Direct GET success: {books}")

    finally:
        await api_client.aclose()


from bson import ObjectId


@pytest.mark.asyncio
async def test_debug_client_lifecycle(async_client_factory, test_book):
    """Debug the async client factory lifecycle"""

    print(f"\n=== Test 1 Start ===")
    print(f"Thread: {threading.current_thread().name}")
    print(f"Thread ID: {threading.get_ident()}")

    try:
        loop = asyncio.get_event_loop()
        print(
            f"Loop before client: {id(loop)}, running: {loop.is_running()}, closed: {loop.is_closed()}"
        )
    except Exception as e:
        print(f"Can't get loop before client: {e}")

    print("Creating client...")
    api_client = await async_client_factory()
    print(f"Client created: {type(api_client)}")

    try:
        loop = asyncio.get_event_loop()
        print(
            f"Loop after client: {id(loop)}, running: {loop.is_running()}, closed: {loop.is_closed()}"
        )
        print(f"Tasks after client: {len(asyncio.all_tasks(loop))}")
    except Exception as e:
        print(f"Can't get loop after client: {e}")

    try:
        payload = test_book.copy()
        payload["owner_id"] = str(test_book["owner_id"])
        del payload["_id"]
        del payload["id"]
        del payload["toc_items"]
        del payload["published"]
        payload_book = jsonable_encoder(payload)

        print("Making request...")
        response = await api_client.post(f"/api/v1/books/", json=payload_book)
        print(f"Response: {response.status_code}")

        try:
            loop = asyncio.get_event_loop()
            print(
                f"Loop after request: {id(loop)}, running: {loop.is_running()}, closed: {loop.is_closed()}"
            )
            print(f"Tasks after request: {len(asyncio.all_tasks(loop))}")
        except Exception as e:
            print(f"Can't get loop after request: {e}")

    except Exception as e:
        print(f"Request failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        print("Closing client...")
        try:
            await api_client.aclose()
            print("Client closed successfully")

            try:
                loop = asyncio.get_event_loop()
                print(
                    f"Loop after close: {id(loop)}, running: {loop.is_running()}, closed: {loop.is_closed()}"
                )
                print(f"Tasks after close: {len(asyncio.all_tasks(loop))}")
            except Exception as e:
                print(f"Can't get loop after close: {e}")

        except Exception as e:
            print(f"Error closing client: {e}")

    print(f"=== Test 1 End ===\n")


@pytest.mark.asyncio
async def test_debug_second_client(async_client_factory, test_book):
    """Debug what happens in the second test"""

    print(f"\n=== Test 2 Start ===")
    print(f"Thread: {threading.current_thread().name}")
    print(f"Thread ID: {threading.get_ident()}")

    try:
        loop = asyncio.get_event_loop()
        print(
            f"Test 2 initial loop: {id(loop)}, running: {loop.is_running()}, closed: {loop.is_closed()}"
        )
        print(f"Test 2 initial tasks: {len(asyncio.all_tasks(loop))}")

        # Print all task details
        for i, task in enumerate(asyncio.all_tasks(loop)):
            print(
                f"  Task {i}: {task}, done: {task.done()}, cancelled: {task.cancelled()}"
            )

    except Exception as e:
        print(f"Test 2 can't get loop: {e}")

    print("Test 2 creating client...")
    try:
        api_client = await async_client_factory()
        print(f"Test 2 client created: {type(api_client)}")

        try:
            loop = asyncio.get_event_loop()
            print(
                f"Test 2 loop after client: {id(loop)}, running: {loop.is_running()}, closed: {loop.is_closed()}"
            )
        except Exception as e:
            print(f"Test 2 can't get loop after client: {e}")

        payload = test_book.copy()
        payload["owner_id"] = str(test_book["owner_id"])
        del payload["_id"]
        del payload["id"]
        del payload["toc_items"]
        del payload["published"]
        payload_book = jsonable_encoder(payload)

        print("Test 2 making request...")
        response = await api_client.post(f"/api/v1/books/", json=payload_book)
        print(f"Test 2 response: {response.status_code}")

        if response.status_code != 201:
            print(f"Test 2 error response: {response.text}")

    except Exception as e:
        print(f"Test 2 failed: {e}")
        import traceback

        traceback.print_exc()

    finally:
        try:
            await api_client.aclose()
            print("Test 2 client closed")
        except Exception as e:
            print(f"Test 2 error closing: {e}")

    print(f"=== Test 2 End ===\n")


from app.db import base
import app.db.book as book_dao


@pytest.mark.asyncio
async def test_dao_method_calls():
    """Test if DAO methods are being called correctly"""

    print("\n=== Testing DAO Method Calls ===")

    # Test book creation directly
    try:
        print("Testing book DAO create_book...")

        book_data = {
            "title": "Test Book DAO Call",
            "subtitle": "Test Subtitle",
            "description": "Test Description",
            "genre": "Fiction",
            "target_audience": "Adults",
            "owner_id": "test_owner",
            "metadata": {},
        }

        # Check if create_book exists and what it expects
        if hasattr(book_dao, "create_book"):
            print(f"create_book function found: {book_dao.create_book}")

            # Try calling it
            result = await book_dao.create_book(book_data)
            print(f"create_book result: {result}")
        else:
            print("create_book function not found in book_dao")

    except Exception as e:
        print(f"Error calling create_book: {e}")
        import traceback

        traceback.print_exc()

    # Test collection methods directly
    try:
        print("\nTesting collection methods directly...")

        collection = base.books_collection
        print(f"Collection type: {type(collection)}")

        # Test insert_one
        doc = {"test": "data"}
        result = await collection.insert_one(doc)
        print(f"insert_one result: {result}")

        # Test find_one
        found = await collection.find_one({"test": "data"})
        print(f"find_one result: {found}")

    except Exception as e:
        print(f"Error with collection methods: {e}")
        import traceback

        traceback.print_exc()

    print("=== End DAO Method Test ===\n")


import inspect


def test_check_imports():
    """Check what functions are being imported and their signatures"""

    print("\n=== Checking Imports ===")

    try:
        # Check app.db.database imports
        print("Checking app.db.database...")
        from app.db.database import create_book as db_create_book

        print(f"database.create_book: {db_create_book}")
        print(f"database.create_book signature: {inspect.signature(db_create_book)}")
        print(
            f"database.create_book is async: {inspect.iscoroutinefunction(db_create_book)}"
        )

    except ImportError as e:
        print(f"Could not import from app.db.database: {e}")

    try:
        # Check app.db.book imports
        print("\nChecking app.db.book...")
        import app.db.book as book_dao

        if hasattr(book_dao, "create_book"):
            book_create_book = book_dao.create_book
            print(f"book_dao.create_book: {book_create_book}")
            print(
                f"book_dao.create_book signature: {inspect.signature(book_create_book)}"
            )
            print(
                f"book_dao.create_book is async: {inspect.iscoroutinefunction(book_create_book)}"
            )
        else:
            print("create_book not found in book_dao")

    except ImportError as e:
        print(f"Could not import app.db.book: {e}")

    try:
        # Check what functions are available in each module
        print("\nAvailable functions in app.db.database:")
        import app.db.database as db_module

        for name in dir(db_module):
            if not name.startswith("_"):
                func = getattr(db_module, name)
                if callable(func):
                    print(f"  {name}: {func}")

    except ImportError as e:
        print(f"Could not import app.db.database module: {e}")

    try:
        print("\nAvailable functions in app.db.book:")
        import app.db.book as book_module

        for name in dir(book_module):
            if not name.startswith("_"):
                func = getattr(book_module, name)
                if callable(func):
                    print(f"  {name}: {func}")

    except ImportError as e:
        print(f"Could not import app.db.book module: {e}")

    print("=== End Import Check ===\n")


async def test_first_simple_post(auth_client_factory, test_book):
    """Simple POST test that should work"""
    client = await auth_client_factory()

    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)

    print("\n=== FIRST TEST - POST only ===")
    response = await client.post("/api/v1/books/", json=payload_book)
    print(f"POST response: {response.status_code}")

    if response.status_code != 201:
        print(f"POST error: {response.text}")
    else:
        print("POST succeeded")

    assert response.status_code == 201


async def test_second_simple_post(auth_client_factory, test_book):
    """Identical POST test to see if it fails"""
    client = await auth_client_factory()

    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)

    print("\n=== SECOND TEST - POST only ===")
    response = await client.post("/api/v1/books/", json=payload_book)
    print(f"POST response: {response.status_code}")

    if response.status_code != 201:
        print(f"POST error: {response.text}")
    else:
        print("POST succeeded")

    assert response.status_code == 201


async def test_third_simple_post(auth_client_factory, test_book):
    """Third identical POST test"""
    client = await auth_client_factory()

    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)

    print("\n=== THIRD TEST - POST only ===")
    response = await client.post("/api/v1/books/", json=payload_book)
    print(f"POST response: {response.status_code}")

    if response.status_code != 201:
        print(f"POST error: {response.text}")
    else:
        print("POST succeeded")

    assert response.status_code == 201


async def test_check_auth_client_factory_state(auth_client_factory, test_book):
    """Check if the auth_client_factory itself is the issue"""
    print("\n=== FOURTH TEST - Check factory state ===")

    # Check database state before creating client

    try:
        # See what's in the collections
        books_count = len(
            asyncio.get_event_loop().run_until_complete(
                base.books_collection.find({}).to_list(length=100)
            )
        )
        users_count = len(
            asyncio.get_event_loop().run_until_complete(
                base.users_collection.find({}).to_list(length=100)
            )
        )
        print(f"Before client creation - Books: {books_count}, Users: {users_count}")
    except Exception as e:
        print(f"Error checking DB state: {e}")

    client = await auth_client_factory()
    print("Client created successfully")

    # Check again after client creation
    try:
        books_count = len(
            asyncio.get_event_loop().run_until_complete(
                base.books_collection.find({}).to_list(length=100)
            )
        )
        users_count = len(
            asyncio.get_event_loop().run_until_complete(
                base.users_collection.find({}).to_list(length=100)
            )
        )
        print(f"After client creation - Books: {books_count}, Users: {users_count}")
    except Exception as e:
        print(f"Error checking DB state after client: {e}")

    payload = test_book.copy()
    payload["owner_id"] = str(test_book["owner_id"])
    del payload["_id"]
    del payload["id"]
    del payload["toc_items"]
    del payload["published"]
    payload_book = jsonable_encoder(payload)

    response = await client.post("/api/v1/books/", json=payload_book)
    print(f"POST response: {response.status_code}")

    if response.status_code != 201:
        print(f"POST error: {response.text}")

    assert response.status_code == 201


def test_debug_collection_types_first():
    """Debug what type of collections we have"""
    from app.db import base

    print(f"\n=== FIRST TEST COLLECTION TYPES ===")
    print(f"books_collection type: {type(base.books_collection)}")
    print(f"books_collection: {base.books_collection}")
    print(f"users_collection type: {type(base.users_collection)}")


def test_debug_collection_types_second():
    """Debug what type of collections we have in second test"""
    from app.db import base

    print(f"\n=== SECOND TEST COLLECTION TYPES ===")
    print(f"books_collection type: {type(base.books_collection)}")
    print(f"books_collection: {base.books_collection}")
    print(f"users_collection type: {type(base.users_collection)}")


def test_debug_collection_types_third():
    """Debug what type of collections we have in third test"""
    from app.db import base

    print(f"\n=== THIRD TEST COLLECTION TYPES ===")
    print(f"books_collection type: {type(base.books_collection)}")
    print(f"books_collection: {base.books_collection}")
    print(f"users_collection type: {type(base.users_collection)}")
