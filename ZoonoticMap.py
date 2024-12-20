import os
import pandas as pd
from Bio import SeqIO
import subprocess

# Define category weights and risk levels
CATEGORY_WEIGHTS = {
    'Adherence': 4,
    'Biofilm': 3,
    'Efflux': 4,
    'Exotoxin': 5,
    'Resistance': 4,
    'T3SS': 5,
    'T4SS': 5,
    'T6SS': 5,
    'Integrative_Conjugative_Element': 4
}

RISK_LEVELS = {
    "High Risk of pathogenicity and Zoonotic potential": lambda score: score >= 30,
    "Moderate Risk of pathogenicity and Zoonotic potential": lambda score: 15 <= score < 30,
    "Low Risk of pathogenicity and Zoonotic potential": lambda score: score < 15
}

def create_annotations_file(fasta_file, output_file):
    """Create annotations TSV file from a FASTA file."""
    if os.path.exists(output_file):
        print(f"Annotations file already exists at {output_file}. Skipping regeneration.")
        return
    
    categories = {
        'ICEberg|': 'Integrative_Conjugative_Element',
        'resfinderf': 'Resistance',
        'PID|': 'T4SS',
        # Add other patterns as needed
    }
    
    annotations = []
    for record in SeqIO.parse(fasta_file, "fasta"):
        seq_id = record.id
        header = record.description
        category = "Unknown"
        for keyword, cat in categories.items():
            if keyword in header:
                category = cat
                break
        annotations.append((seq_id, category))
    
    # Save annotations
    with open(output_file, "w") as out_file:
        out_file.write("sseqid\tCategory\n")
        for seq_id, category in annotations:
            out_file.write(f"{seq_id}\t{category}\n")
    print(f"Annotations file saved to {output_file}")

def run_blast(query_file, db_path, output_file):
    """Run BLAST and save results."""
    command = [
        "blastn", 
        "-query", query_file, 
        "-db", db_path, 
        "-out", output_file, 
        "-outfmt", "6 qseqid sseqid pident length mismatch gapopen qstart qend sstart send evalue bitscore"
    ]
    subprocess.run(command, check=True)

def parse_blast_results(blast_results_file, annotation_file):
    """Parse BLAST results and merge with annotations."""
    annotations = pd.read_csv(annotation_file, sep="\t")
    blast_results = pd.read_csv(blast_results_file, sep="\t", header=None, names=[
        "qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
        "qstart", "qend", "sstart", "send", "evalue", "bitscore"
    ])
    merged = pd.merge(blast_results, annotations, on="sseqid", how="left")
    return merged

def calculate_scores_and_risks(results):
    """Calculate scores and risk levels."""
    category_counts = results['Category'].value_counts().to_dict()
    total_score = sum(CATEGORY_WEIGHTS.get(category, 0) for category in category_counts.keys())
    risk_level = next(level for level, condition in RISK_LEVELS.items() if condition(total_score))
    return category_counts, total_score, risk_level

def main():
    query_file = r"C:\Users\Lenovo\Desktop\blast\query_genome.fasta"
    db_path = r"C:\Users\Lenovo\Desktop\blast\blast_db"
    blast_results_file = r"C:\Users\Lenovo\Desktop\blast\blast_results.tsv"
    annotation_file = r"C:\Users\Lenovo\Desktop\blast\annotations.tsv"
    final_excel = r"C:\Users\Lenovo\Desktop\blast\final_results.xlsx"

    # Create annotations if not present
    reference_file = r"C:\Users\Lenovo\Desktop\blast\cleaned_references_processed.fasta"
    create_annotations_file(reference_file, annotation_file)

    # Run BLAST
    run_blast(query_file, db_path, blast_results_file)

    # Parse results
    results = parse_blast_results(blast_results_file, annotation_file)

    # Filter matches with ≥95% identity
    filtered_results = results[results['pident'] >= 95]

    # Calculate scores and risks
    category_counts, total_score, risk_level = calculate_scores_and_risks(filtered_results)

    # Save to Excel
    with pd.ExcelWriter(final_excel) as writer:
        filtered_results.to_excel(writer, index=False, sheet_name="Filtered Matches")
        summary = pd.DataFrame([{
            "Total Score": total_score,
            "Risk Level": risk_level,
            **category_counts
        }])
        summary.to_excel(writer, index=False, sheet_name="Summary")

    print(f"Results saved to {final_excel}")

if __name__ == "__main__":
    main()
