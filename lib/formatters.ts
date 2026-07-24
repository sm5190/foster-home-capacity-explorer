const integerFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 0,
});

export function formatInteger(value: number): string {
  return integerFormatter.format(value);
}

export function formatDecimal(
  value: number | null,
  maximumFractionDigits = 1,
): string {
  if (value === null) {
    return "Not available";
  }

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  }).format(value);
}

export function formatPercentage(
  value: number | null,
  maximumFractionDigits = 1,
): string {
  if (value === null) {
    return "Not available";
  }

  return new Intl.NumberFormat("en-US", {
    style: "percent",
    minimumFractionDigits: maximumFractionDigits,
    maximumFractionDigits,
  }).format(value);
}
