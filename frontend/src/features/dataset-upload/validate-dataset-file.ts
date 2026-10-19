const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

export function validateDatasetFile(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return "Choose a CSV file to continue.";
  }

  if (file.size === 0) {
    return "The CSV file is empty.";
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return "The CSV file must be 10 MB or smaller.";
  }

  return null;
}

export function formatFileSize(sizeInBytes: number): string {
  if (sizeInBytes < 1024) {
    return `${sizeInBytes} B`;
  }

  return `${(sizeInBytes / 1024).toFixed(1)} KB`;
}
