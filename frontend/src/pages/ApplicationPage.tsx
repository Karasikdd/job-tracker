import { useParams } from "react-router";

export function ApplicationPage() {
  const { id } = useParams();

  return (
    <section>
      <h1>Application details</h1>
      <p>Application ID: {id}</p>
    </section>
  );
}