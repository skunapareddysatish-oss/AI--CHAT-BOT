from app.memory import init_db, add_message, get_history

init_db()

add_message("user1", "user", "Hello")
add_message("user1", "assistant", "Hi! How can I help?")
add_message("user1", "user", "What is FastAPI?")

history = get_history("user1")

print(history)