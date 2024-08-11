import sys
import pandas as pd
import glob
import argparse

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Merge Parquet files and write to output file.")
    parser.add_argument("-o", "--output", required=True, help="Output file path")
    parser.add_argument("input_files", nargs="*", help="Input Parquet file paths or patterns")
    args = parser.parse_args()

    # Check if file paths are provided as command-line arguments
    if args.input_files:
        pattern_paths = args.input_files
        # Expand patterns to actual file paths
        file_paths = []
        for pattern in pattern_paths:
            file_paths.extend(glob.glob(pattern))
    else:
        # Read list of Parquet files from standard input
        file_paths = [line.strip() for line in sys.stdin]
    
    if not file_paths:
        print("Please provide at least one Parquet file as input.")
        sys.exit(1)
    
    # Read and merge Parquet files
    dfs = [pd.read_parquet(file_path, engine="pyarrow") for file_path in file_paths]
    merged_df = pd.concat(dfs, ignore_index=True)

    # Write merged DataFrame to the specified output file
    merged_df.to_parquet(args.output, engine="pyarrow")
    print(f"Merged data written to {args.output}")