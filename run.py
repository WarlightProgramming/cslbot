# compute.py
## runs everything (infinite loop)

# imports
from main import run

# run everything
if __name__ == '__main__':
    while True:
        try: run()
        except KeyboardInterrupt: break
