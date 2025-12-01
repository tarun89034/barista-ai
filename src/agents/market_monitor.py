import time
import random

class MarketMonitor:
    def __init__(self, threshold_price_change=0.05, threshold_volume_spike=1.5):
        self.previous_price = None
        self.previous_volume = None
        self.threshold_price_change = threshold_price_change
        self.threshold_volume_spike = threshold_volume_spike

    def get_market_data(self):
        # In practice, this method should retrieve data from a market API
        price = random.uniform(100, 200)  # Simulated price
        volume = random.uniform(10, 100)   # Simulated volume
        return price, volume

    def monitor(self):
        while True:
            price, volume = self.get_market_data()
            if self.previous_price is not None:
                price_change = (price - self.previous_price) / self.previous_price
                if abs(price_change) >= self.threshold_price_change:
                    print(f"Price Change Detected: {price_change:.2%} - New Price: {price}")

            if self.previous_volume is not None:
                volume_spike = volume / self.previous_volume
                if volume_spike >= self.threshold_volume_spike:
                    print(f"Volume Spike Detected: {volume_spike:.2f} - New Volume: {volume}")

            self.previous_price = price
            self.previous_volume = volume
            time.sleep(5)  # Delay for demonstration purposes

if __name__ == "__main__":
    monitor = MarketMonitor()
    monitor.monitor()