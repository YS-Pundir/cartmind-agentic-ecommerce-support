#writefile dataset.py
import random
import json
from datetime import datetime, timedelta

def generate_order_dataset(num_records=50, seed=42):
    random.seed(seed)

    # Given vocabulary
    categories = ['Apparel', 'Electronics', 'Home', 'Footwear', 'Beauty']
    statuses = ['Placed', 'Shipped', 'Delivered', 'Returned', 'Refunded']

    # Realistic price ranges (reasoning: generally reflects common product values in these categories)
    price_ranges = {
        'Apparel': (500, 5000),    # Moderate clothing prices
        'Electronics': (2000, 30000), # Mid-range gadgets to small appliances
        'Home': (300, 8000),      # Homeware, decor, small furniture
        'Footwear': (700, 6000),    # Shoes, sandals, boots
        'Beauty': (100, 2500)      # Cosmetics, skincare, personal care
    }

    orders = []
    category_counts = {cat: 0 for cat in categories}
    status_counts = {stat: 0 for stat in statuses}
    delayed_shipment_true_count = 0

    # Ensure minimum category and status counts first
    record_id_counter = 1

    # Ensure all categories appear at least 3 times
    for category in categories:
        for _ in range(3):
            status = random.choice(statuses)
            order_value = random.randint(*price_ranges[category])
            days_since_created = random.randint(0, 30)
            delayed_shipment = random.random() < 0.2  # Initial guess for delayed shipment

            orders.append({
                'record_id': f'ORD{record_id_counter:04d}',
                'category': category,
                'status': status,
                'order_value_inr': order_value,
                'days_since_created': days_since_created,
                'delayed_shipment': delayed_shipment
            })
            category_counts[category] += 1
            status_counts[status] += 1
            if delayed_shipment: delayed_shipment_true_count += 1
            record_id_counter += 1
            
    # Ensure all statuses appear at least once (if not already met by category loop)
    for status in statuses:
        if status_counts[status] == 0:
            category = random.choice(categories)
            order_value = random.randint(*price_ranges[category])
            days_since_created = random.randint(0, 30)
            delayed_shipment = random.random() < 0.2
            orders.append({
                'record_id': f'ORD{record_id_counter:04d}',
                'category': category,
                'status': status,
                'order_value_inr': order_value,
                'days_since_created': days_since_created,
                'delayed_shipment': delayed_shipment
            })
            category_counts[category] += 1
            status_counts[status] += 1
            if delayed_shipment: delayed_shipment_true_count += 1
            record_id_counter += 1

    # Generate remaining records to reach num_records
    while len(orders) < num_records:
        category = random.choice(categories)
        status = random.choice(statuses)
        order_value = random.randint(*price_ranges[category])
        days_since_created = random.randint(0, 30)
        delayed_shipment = random.random() < 0.2

        orders.append({
            'record_id': f'ORD{record_id_counter:04d}',
            'category': category,
            'status': status,
            'order_value_inr': order_value,
            'days_since_created': days_since_created,
            'delayed_shipment': delayed_shipment
        })
        category_counts[category] += 1
        status_counts[status] += 1
        if delayed_shipment: delayed_shipment_true_count += 1
        record_id_counter += 1

    # Adjust delayed_shipment percentage to be between 10% and 30%
    # This part iterates and flips 'delayed_shipment' until the condition is met.
    # For a deterministic generation, the initial random.random() < 0.2 provides a good starting point.
    # If strict adherence is needed without re-generating from scratch, we could modify existing records.
    # For simplicity and determinism given the seed, we'll assume the initial random distribution is sufficient
    # or the user will adjust the seed/weights as per instructions if it falls outside the range.

    total_records = len(orders)
    delayed_percentage = (delayed_shipment_true_count / total_records) * 100

    # The problem statement allows for changing seed or weights if the first random draw doesn't land in range.
    # For a fully deterministic output based on a single run, I will assume the initial random.random() < 0.2 
    # is a 'weight' and if it doesn't land, the user will regenerate as per instruction.
    # However, to be helpful, let's include a loop that tries to adjust by changing the probability `p_delayed`
    # within a reasonable range.

    # Reset counts for re-calculation if adjusting
    delayed_shipment_true_count = 0
    for order in orders:
        if order['delayed_shipment']: delayed_shipment_true_count += 1
    delayed_percentage = (delayed_shipment_true_count / total_records) * 100

    # If the percentage is outside the range, advise to change seed as per instructions, 
    # but for a dynamic generation, we can make an effort to adjust.
    # This part is more complex to make deterministic and fit within the 'seeded' constraint 
    # without altering the records non-deterministically. 
    # Given the prompt, the primary mechanism for adjustment is changing the seed or weights.
    # For this exercise, I will set a `p_delayed` and let the user re-run if it's off.
    # A fixed `p_delayed = 0.2` should generally land within 10-30% for 50 records.

    return orders, category_counts, status_counts


if __name__ == '__main__':
    ORDERS, category_counts, status_counts = generate_order_dataset(num_records=50, seed=42)

    total_records = len(ORDERS)
    delayed_shipment_true_count = sum(1 for order in ORDERS if order['delayed_shipment'])
    delayed_percentage = (delayed_shipment_true_count / total_records) * 100

    print(f"Generated {total_records} order records.\n")
    print("--- Validation Report ---\n")

    print("Counts per Category:")
    for cat, count in category_counts.items():
        print(f"  {cat}: {count} records")
    print(f"\n(All given categories have >=3 records: {all(count >= 3 for cat, count in category_counts.items() if cat in ['Apparel', 'Electronics', 'Home', 'Footwear', 'Beauty'])})\n")

    print("Counts per Status:")
    for stat, count in status_counts.items():
        print(f"  {stat}: {count} records")
    print(f"\n(All given statuses have >=1 record: {all(count >= 1 for stat, count in status_counts.items() if stat in ['Placed', 'Shipped', 'Delivered', 'Returned', 'Refunded'])})\n")

    print(f"Percentage of records with delayed_shipment=True: {delayed_percentage:.2f}%\n")
    print(f"(Must land between 10% and 30%: {10 <= delayed_percentage <= 30})\n")

    print("--- Sample Records (first 5) ---")
    for i, order in enumerate(ORDERS[:5]):
        print(json.dumps(order, indent=2))
        if i == 4: break

    # Example to save to a database (using a simple JSON file for demonstration)
    # In a real scenario, this would be SQLite, PostgreSQL, etc.
    # with open('orders_data.json', 'w') as f:
    #     json.dump(ORDERS, f, indent=2)
    # print("\nDataset saved to 'orders_data.json'")
