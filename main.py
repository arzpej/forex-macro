from src.FED_US import get_all_fred, clean_fred
from src.ECB_EU import get_all_ecb, clean_ecb
from src.CHINA_CN import get_all_china, clean_china

# --- US ---
get_all_fred()
us = clean_fred()
print("US:", us.shape)
print(us.tail())

# --- Europe ---
get_all_ecb()
eu = clean_ecb()
print("EU:", eu.shape)
print(eu.tail())

# --- China ---
get_all_china()
cn = clean_china()
print("CN:", cn.shape)
print(cn.tail())
 