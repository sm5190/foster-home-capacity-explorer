export class CountyNotFoundError extends Error {
  constructor(public readonly countySlug: string) {
    super(`County aggregate was not found for slug: ${countySlug}`);

    this.name = "CountyNotFoundError";
  }
}
