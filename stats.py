import pickle
import os
import csv

def print_dict_tree(d, indent=0, file=None):
    """Recursively print a dictionary as a tree."""
    for key, value in d.items():
        if file:
            file.write('    ' * indent + str(key) + '\n')
        else:
            print('    ' * indent + str(key))
        if isinstance(value, dict):
            print_dict_tree(value, indent + 1, file=file)
        else:
            if file:
                file.write('    ' * (indent + 1) + str(value) + '\n')
            else:
                print('    ' * (indent + 1) + str(value))

def dict_to_csv(data, csv_filename):
    """
    Write a dictionary of dictionaries to a CSV file.
    Rows: top-level keys
    Columns: all unique sub-keys
    """
    # Collect all unique sub-keys and sub-sub-keys
    all_columns = set()
    for v in data.values():
        if isinstance(v, dict):
            for subk, subv in v.items():
                if isinstance(subv, dict):
                    for subsubk in subv.keys():
                        all_columns.add(f"{subk}.{subsubk}")
                else:
                    all_columns.add(subk)
    all_columns = sorted(all_columns)

    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['ID'] + all_columns)
        for k, v in data.items():
            row = [k]
            values = {}
            if isinstance(v, dict):
                for subk, subv in v.items():
                    if isinstance(subv, dict):
                        for subsubk, val in subv.items():
                            values[f"{subk}.{subsubk}"] = val
                    else:
                        values[subk] = subv
            row += [values.get(col, '') for col in all_columns]
            writer.writerow(row)

def main():
    with open(os.path.join("stats", "stats.pkl"), 'rb') as f:
        data = pickle.load(f)
    with open('output.txt', 'w', newline='') as txtfile:
        print_dict_tree(data, file=txtfile)
    dict_to_csv(data, 'output.csv')

if __name__ == "__main__":
    main()