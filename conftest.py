import sys
import os

current_directory = os.path.dirname(os.path.abspath(__file__))
src_directory = os.path.join(current_directory, 'src')

# Insert the 'src' directory into sys.path
sys.path.insert(0, src_directory)