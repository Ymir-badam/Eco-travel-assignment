
def emission_band(
    kg_co2e,
):

    if kg_co2e <= 20:
        return "low"

    if kg_co2e <= 100:
        return "medium"

    return "high"


def rank_options(options):

    ranked = []

    for option in options:

        carbon = float(
            option.get(
                "carbon_kg",
                0,
            )
        )

        price = float(
            option.get(
                "price",
                0,
            )
        )

        score = (
            carbon * 0.6
            + price * 0.4
        )

        item = dict(option)

        item["score"] = round(
            score,
            2,
        )

        ranked.append(item)

    return sorted(
        ranked,
        key=lambda x: x["score"],
    )
