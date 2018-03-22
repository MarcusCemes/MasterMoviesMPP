import pytest
import sys

def main():
    print('Extracted arg is ==> %s' % sys.argv[2])
    pytest.main([sys.argv[1]])

if __name__ == '__main__':
    main()
