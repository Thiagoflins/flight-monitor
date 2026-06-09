export interface FlightRecord {
  checkedAt: string;
  routeName: string;
  origin: string;
  destination: string;
  departureAt: string;
  returnAt: string | null;
  price: number;
  currency: string;
  airline: string;
  transfers: number | null;
  link: string;
}
