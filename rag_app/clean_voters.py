import pandas as pd

# Read the CSV file
input_file = 'voters._translated.csv'
output_file = 'voters_translated_cleaned.csv'

df = pd.read_csv(input_file)

print(f"Original shape: {df.shape}")
print(f"Original columns: {list(df.columns)}")

# Remove the specified columns
df_cleaned = df.drop(columns=['Father/Husband_Name_English', 'Name_English'])

print(f"\nCleaned shape: {df_cleaned.shape}")
print(f"Cleaned columns: {list(df_cleaned.columns)}")

# Save to new file
df_cleaned.to_csv(output_file, index=False)

print(f"\n✓ File saved: {output_file}")
print(f"✓ Rows preserved: {df_cleaned.shape[0]}")
print(f"✓ Columns reduced: {df.shape[1]} → {df_cleaned.shape[1]}")
