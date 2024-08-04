import pandas as pd

from decimal import Decimal, getcontext, ROUND_HALF_UP


# Define the column mapping
column_pairs = {
    'ItemNameInternal': 'Name*',  # working
    'ItemStatus': 'isGMActive',  # working
    'DescCust': 'Long Description*',  # working
    'SupplierRrp': 'OriginalPrice*',  # working
    'TaxCategory': 'vatRate',  # working
    'DishType': 'Meal Type*',  # working
    'Cuisine': 'Cuisines Tag*',  # working
    'Categories': 'Meal Time*',  # working
    'ServingTemperature': 'isHOT*',  # working
    'SizeMinQty': 'GM min quantity'  # working
}

PRECISION = 5
DIGITS = 2

# creating rounding function for incl tax vendor price
round_context = getcontext()
round_context.rounding = ROUND_HALF_UP


def c_round(x):
    tmp = round(Decimal(x), PRECISION)
    return float(tmp.__round__(DIGITS))


# Removes spaces from inventory names or empty flavourNames in inventory
def text_strip(text):
    return text.strip()


def cast_to_boolean_is_gm_active(is_gm_active):
    if is_gm_active == 'Active':
        return 'TRUE'

    return 'FALSE'


def process_meal_time(meal_time):
    if pd.isna(meal_time):
        return 'Lunch'

    options = meal_time.split('|')

    for preferred_option in ['Lunch', 'Dinner', 'Breakfast']:
        if preferred_option in options:
            return preferred_option

    return 'Lunch'


# Change format of VAT Rate to fit format
def process_vat_rate(value):
    if value == 'VatApplicableUk':
        return 0.20
    elif value == 'GstApplicableAu':
        return 0.10
    elif value == 'GstApplicableSg':
        return 0.09
    elif value == 'GstApplicableNz':
        return 0.15
    elif value == 'GstVatExempt':
        return 0
    # Add more conditions here if needed
    return value


# Set Meals to be Hot
def process_hot_meals(value):
    if value == 'Hot':
        return 'TRUE'
    elif value == 'Cold':
        return 'FALSE'
    return value


# Replaces names to correct names
def process_allergens_list(allergen_list):
    allergen_list = list(map(lambda x: x.replace('gluten', 'contains gluten'), allergen_list))
    allergen_list = list(map(lambda x: x.replace('dairy', 'milk'), allergen_list))
    allergen_list = list(map(lambda x: x.replace('soy', 'soybeans'), allergen_list))
    allergen_list = list(map(lambda x: x.replace('sesame seeds', 'sesame'), allergen_list))
    allergen_list = list(map(lambda x: x.replace('sulphur dioxide and sulphites', 'sulphites'), allergen_list))
    # add other allergens here

    return allergen_list


# Read the input CSV
input_file = input("Enter the name of the input CSV file (e.g., input.csv): ")
input_data = pd.read_csv(input_file)

# Read the output CSV template
output_template_file = 'output_template.csv'
output_template = pd.read_csv(output_template_file)

# Create a DataFrame with the output CSV column headers
output_data = pd.DataFrame(columns=output_template.columns)

# Map the columns from the input data to the output data
for input_column, output_column in column_pairs.items():
    if input_column in input_data.columns and output_column in output_template.columns:
        output_data[output_column] = input_data[input_column]

# Map the Allergens column
output_data['Allergens'] = input_data['Allergens']

# Map dietaries column
output_data['Dietaries'] = input_data['DietPreferences']

# Map and concatenate FlavourName and ItemName
output_data['Name*'] = output_data['Name*'].apply(text_strip)
input_data['FlavourName'] = input_data['FlavourName'].fillna(' ')
input_data['FlavourName'] = input_data['FlavourName'].apply(text_strip)
output_data['Name*'] = input_data['FlavourName'] + ' ' + output_data['Name*']
output_data['Name*'] = output_data['Name*'].apply(text_strip)

# Process the data format changes in columns
output_data['Meal Time*'] = output_data['Meal Time*'].apply(process_meal_time)
output_data['vatRate'] = output_data['vatRate'].apply(process_vat_rate)
output_data['isHOT*'] = output_data['isHOT*'].apply(process_hot_meals)

# Edit values for incl tax vendor price
output_data['OriginalPrice*'] = output_data['OriginalPrice*'] * (1 + output_data['vatRate'].apply(float))
output_data['OriginalPrice*'] = output_data['OriginalPrice*'].apply(c_round)

# Change values to booleans
output_data['isGMActive'] = output_data['isGMActive'].apply(cast_to_boolean_is_gm_active)

# Set default values for Required* columns
output_data['Meal Type*'] = output_data['Meal Type*'].fillna('Main')
# Not sure if this is right (replacing None with Main)
output_data['Long Description*'] = output_data['Long Description*'].fillna('Not provided')
output_data['Short Description*'] = output_data['Long Description*'].fillna('Not provided')
output_data['isMenuItem*'] = output_data['isMenuItem*'].fillna('TRUE')
output_data['isOption*'] = output_data['isOption*'].fillna('FALSE')
output_data['isCCActive'] = output_data['isCCActive'].fillna('FALSE')
# ­ is a unicode character that is a really tiny hyphen (you cannot insert a space into a spreadsheet)
output_data['Ingredients*'] = output_data['Ingredients*'].fillna('­')

# Map dietaries column
output_data['Dietaries'] = input_data['DietPreferences']

# Process the Allergens columns, splitting them into different columns
allergens_columns = [col for col in output_data.columns if col.startswith('Allergen*:')]

# Loop through the rows and columns
#     dairy does not work rn because of the template saying milk and gluten
for index, row in output_data.iterrows():
    allergens = row['Allergens']
    no_allergens = True  # Initialize no_allergens as True by default

    if pd.notna(allergens):
        allergens_list = [item.strip().lower() for item in allergens.split('|')]
        allergens_list = process_allergens_list(allergens_list)

        for allergen_column in allergens_columns:
            if allergen_column != "Allergen*: Contains none of these allergens":
                allergen_name = allergen_column[len('Allergen*: '):].lower()
                is_present = allergen_name in allergens_list
                output_data.at[index, allergen_column] = is_present

                if is_present:
                    no_allergens = False  # Set no_allergens to False if an allergen is present
    else:
        for allergen_column in allergens_columns:
            output_data.at[index, allergen_column] = False

    output_data.at[index, "Allergen*: Contains none of these allergens"] = no_allergens

# Process Dietaries columns splitting them into different columns
dietaries_columns = [col for col in output_data.columns if col.startswith('Dietary:')]

# Loop through the rows and columns
for index, row in output_data.iterrows():
    dietaries = row['Dietaries']
    if pd.notna(dietaries):
        dietaries_list = [item.strip().lower() for item in dietaries.split('|')]
        for dietaries_column in dietaries_columns:
            dietaries_name = dietaries_column[len('Dietary: '):].lower()
            is_present = dietaries_name in dietaries_list
            output_data.at[index, dietaries_column] = is_present
    else:
        for dietaries_column in dietaries_columns:
            output_data.at[index, dietaries_column] = False

# Remove the 'Dietaries' and 'Allergens' columns from the output DataFrame so that they're appended to the CSV
output_data = output_data.drop(columns=['Dietaries', 'Allergens'])

# For some reason the first row (not title/0th row) does not get turned into a menu item
output_data.loc[len(output_data)] = None
output_data = output_data.shift()

# Removing rows that are not GM Active
output_data = output_data.drop(output_data.index[output_data['isGMActive'] == 'FALSE'].tolist())

# Ask for input and output file names
output_file = input("Enter the name of the output CSV file (e.g., output.csv): ")

# Write the output data to a new CSV file
output_data.to_csv(output_file, index=False)
