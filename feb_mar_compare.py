# from datetime import date
import os
import sys

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
import seaborn as sns

pd.set_option('display.width', None)

# -------------------------------------------------------
# defining necessary variables
main_directory = os.path.dirname(__file__)
today = pd.to_datetime('2024-03-04')
# today = date.today()  # this report was ran on 3/4/2024, I defined it as a static var just for the sake of this demo
sales = []
columns = ['amazon-order-id', 'merchant-order-id', 'purchase-date', 'item-price', 'product-name']
# defining n days passed since enacting the new pricing strategy
days_since_price_change = pd.to_timedelta(today - pd.to_datetime('2024-02-20'), "D").days
brand_to_filter_out = 'REDACTED_2'

# reading in raw sales data
for file in os.listdir(f'{main_directory}/raw data'):
    file_path = os.path.join(f'{main_directory}/raw data', file)
    if file.startswith('README') or not file.endswith('txt'):
        continue
    elif file.endswith('txt'):
        test = pd.read_csv(file_path, sep='\t', nrows=1)
        if all(key in test for key in ['purchase-date', 'signature-confirmation-recommended ']):
            try:
                df = pd.read_csv(file_path, sep='\t', usecols=columns, dtype={'item-price': 'float32'})
                sales.append(df)
            # ensuring that the numeric columns can be aggregated
            except ValueError as ve:
                print(f"{ve}")
                print(f"Please check file `{file}`, it appears to have some non-numeric values in `item-price`.")
                sys.exit()

# concatenate the list of df's into a df, whilst making sure the df is not empty
try:
    sales = pd.concat(sales)
except ValueError as ve:
    print(f"ValueError: {ve}")
    print('It looks like there are 0 necessary txt raw sales files in the specified directory.')
    sys.exit()

# if all the sales files summed return 0 sales, then terminate the program
if sales['item-price'].sum() == 0:
    error = 'There are 0 sales for this time period. ' \
            'If you believe this to be in error, double check the `item-price` column(s).'
    raise ValueError(error)

# cleaning/filtering
try:
    sales = sales.dropna()\
        .drop_duplicates()\
        .query("~`product-name`.str.contains(@brand_to_filter_out, case=False)") \
        .assign(
                purchase_date=lambda x: x['purchase-date'].str.split("T").str[0],
                day=lambda x: pd.to_datetime(x['purchase_date']).dt.strftime('%B-%d'))\
        .drop('purchase-date', axis=1)
except ValueError as ve:
    print(ve)
    print('Check your date columns; you have a row in your date col that is not properly formatted & cannot be parsed.')
    sys.exit()

# ensuring the script stops if you accidentally filter out everything with the query brand filter above
if sales['item-price'].sum() == 0:
    error = 'Your brand filter has excluded all possible sales data. Nothing left to work with.'
    raise ValueError(error)

# converting to pivot table
sales = pd.pivot_table(sales, index=['purchase_date', 'day'], values='item-price', aggfunc='sum') \
    .reset_index()

# splitting sales into two separate df's, by year
sales2023 = sales.query('purchase_date.str.contains("2023")') \
    .assign(MA7=lambda x: x['item-price'].rolling(7, min_periods=0).mean())  # smoothing out the lines for the charts

sales2024 = sales.query('purchase_date.str.contains("2024") & purchase_date != @today.strftime("%Y-%m-%d")') \
    .assign(MA7=lambda x: x['item-price'].rolling(7, min_periods=0).mean())
# note - filtered out the day the report was run to omit a potentially misleading incomplete sales day from the chart

# -------------------------------------------------------
# creating the chart

fig, ax = plt.subplots(figsize=(15, 7))

# line chart for 2024
sns.lineplot(data=sales2024, x='day', y='MA7', linewidth=4, label='2024', c='purple', alpha=.85)

# area chart for 2023 (point of comparison)
plt.stackplot(sales2023['day'], sales2023['MA7'], labels=['2023'], alpha=.25, colors=['green'])

# y axis format
plt.ylabel('Daily Revenue', fontsize=11)
plt.axvline('February-20', c='black', linewidth=1)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, pos: f"${x:,.0f}"))

# x axis format
plt.xlabel('')
plt.xticks(sales2023['day'][::7], rotation=30)

# general formatting
plt.title('Impact of adjusted pricing strategy on revenue', fontsize=18)
plt.grid(axis='y', alpha=.4)
plt.text(15, 7500, 'Changes enacted 02/20 →', c='black', fontsize=10)
plt.legend(prop={'size': 22}, facecolor='white', shadow=True)
plt.tight_layout()

# highlighting the area of interest
ax.add_patch(
    patches.Rectangle(
        (25, 11500),
        days_since_price_change + 2,
        8500,
        linewidth=1,
        alpha=.1,
        facecolor='red'
    )
)

# display/save
plt.show()
# plt.savefig(f'{main_directory}/mar24update.jpg')

