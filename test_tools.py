from app.tools import AVAILABLE_FUNCTIONS

print("Current Time:")
print(AVAILABLE_FUNCTIONS["get_time"]())

print("\nToday's Date:")
print(AVAILABLE_FUNCTIONS["get_date"]())

print("\nCalculator:")
print(AVAILABLE_FUNCTIONS["calculator"]("25*4+100"))

print("\nOrder Status:")
print(AVAILABLE_FUNCTIONS["get_order_status"]("1234"))
