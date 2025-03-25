
import pandas as pd
import random
import string

random.seed(42) # Set the random seed for reproducibility.

def generate_random_string(length=10):
  """Generates a random string of specified length."""
  letters = string.ascii_letters
  return ''.join(random.choice(letters) for _ in range(length))

def generate_random_id(length=8):
  """Generates a random integer ID of specified length."""
  return random.randint(10**(length-1), (10**length)-1)

def synthetic_data_gen(num_rows = 1000):
    data = {
        'store_id': [generate_random_id() for _ in range(num_rows)],
        'store_name': [generate_random_string() for _ in range(num_rows)],
        'region_code': [random.choice(["US", "CA", "UK", "DE", "FR", "JP", "AU"]) for _ in range(num_rows)],
        'store_type': [random.choice(['Supermarket', 'Convenience Store']) for _ in range(num_rows)],
        'num_products': [random.randint(1, 50) for _ in range(num_rows)],
        'num_customers_last_28d': [random.randint(10, 10000) for _ in range(num_rows)],
        'num_customers_last_180d': [random.randint(100, 100000) for _ in range(num_rows)],
        'num_customers_last_365d': [random.randint(1000, 1000000) for _ in range(num_rows)],
        'revenues_last28d': [random.randint(100, 1000000) for _ in range(num_rows)],
        'revenues_last180d': [random.randint(1000, 10000000) for _ in range(num_rows)],
        'revenues_last365d': [random.randint(10000, 100000000) for _ in range(num_rows)],
    }
    return pd.DataFrame(data)

