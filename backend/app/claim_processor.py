from .pipeline import process_document


def process_claim(document_paths):
    """
    Process multiple documents belonging to one insurance claim.
    Each document goes through the existing document pipeline.
    """

    print("\n" + "=" * 70)
    print("CLAIMBRIDGE CLAIM PROCESSING")
    print("=" * 70)

    results = []

    for index, document_path in enumerate(document_paths, start=1):

        print("\n" + "-" * 70)
        print(f"PROCESSING DOCUMENT {index}/{len(document_paths)}")
        print(f"File: {document_path}")
        print("-" * 70)

        try:
            result = process_document(document_path)
            results.append(result)

        except Exception as e:
            print(f"ERROR processing {document_path}: {e}")

            results.append({
                "file": document_path,
                "status": "failed",
                "error": str(e),
            })

    print("\n" + "=" * 70)
    print("CLAIM DOCUMENT PROCESSING COMPLETED")
    print("=" * 70)

    print(f"\nTotal Documents: {len(document_paths)}")
    print(f"Successfully Processed: {sum(1 for r in results if 'extracted_information' in r)}")
    print(f"Failed: {sum(1 for r in results if r.get('status') == 'failed')}")

    return results


if __name__ == "__main__":

    import os

    backend_dir = os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )

    test_documents = [
        os.path.join(
            backend_dir,
            "test_images",
            "sample_bill.jpg"
        ),
    ]

    process_claim(test_documents)