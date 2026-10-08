    # --------------------------------------------------------
    # MARKETING & DESIGN
    # --------------------------------------------------------

    design_title_terms = [
        "visual designer",
        "graphic designer",
        "ui designer",
        "ux designer",
        "ux/ui designer",
        "product designer",
        "brand designer",
        "digital designer",
        "marketing designer",
        "content designer",
        "creative designer",
        "web designer",
    ]

    if any(
        term in title_lower
        for term in design_title_terms
    ):
        return "Marketing & Design"

    if any(
        term in department_lower
        for term in [
            "marketing & design",
            "marketing and design",
            "creative",
            "brand",
            "visual design",
            "graphic design",
            "ux/ui",
        ]
    ):
        return "Marketing & Design"
