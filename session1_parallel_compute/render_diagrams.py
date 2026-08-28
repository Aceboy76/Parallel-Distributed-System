"""
render_diagrams.py - Session 1, Parts 4 and 11.

Renders both Session 1 diagrams to PNG:
    - entity-model-session1.png   (Part 4)
    - architecture-session1.png   (Part 11)

Requires Graphviz to be installed and `dot` available on PATH.

Rebuilt against the actual OULAD monetization schema and the numbers
measured by this pipeline (profile_files.py, load_and_join.py,
partition_strategy.py, sequential_baseline.py, parallel_compute.py,
benchmark.py, partition_analysis.py) - NOT the guide's synthetic
transactions/customers/entitlements/monetization_configs example. In
particular:
    - Event file is studentAssessment.csv (173,912 rows), not a 60,000-row
      transactions.csv.
    - PARTITION_KEY=region has 13 distinct values here, not 50, with a
      measured skew ratio of 2.49:1, not 1.82:1.
    - The rejected alternative id_student is NOT perfectly uniform (28:1
      skew) - it is rejected for being an identifier, not for being
      uniform, which is a different reason than the guide's customer_id
      example.
    - There is an extra prep_oulad.py step before profile_files.py, because
      customers_dim.csv / entitlements_dim.csv / assessment_defs.csv do not
      exist in raw OULAD and must be built first.

Also fixes a string-escaping bug from the original guide script: DOT node
labels need a single literal backslash before "n" for Graphviz to render a
newline (\\n in a Python string), not two literal backslashes (\\\\n in a
Python string), which prints as a stray backslash character instead of
breaking the line.

Run:
    python render_diagrams.py
"""

import subprocess
import sys
from pathlib import Path

import config as cfg

DOCS = cfg.DOCS_DIR
ARCH = cfg.ARCH_DIR
DOCS.mkdir(parents=True, exist_ok=True)
ARCH.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Diagram colours
# ---------------------------------------------------------------------------

NAVY = "#1F3864"
BLUE = "#2E74B5"
LIGHT = "#D9EAF7"
AMBER = "#C55A11"
GREY = "#767171"


# ---------------------------------------------------------------------------
# 1. Entity model (Part 4)
# ---------------------------------------------------------------------------

ENTITY = f"""
digraph EntityModel {{
    rankdir=TB;
    bgcolor="white";
    splines=polyline;
    nodesep=0.9;
    ranksep=1.0;
    fontname="Helvetica";
    labelloc="t";
    fontsize=17;

    label=<<b>CMA-Flow — Session 1 Entity Model</b><br/>
    <font point-size="11">
    OULAD, framed as a Customer / Entitlement / Assessment-Transaction model ·
    multiplicity shown at both ends
    </font><br/> >;

    node [
        shape=plaintext
        fontname="Helvetica"
    ];

    edge [
        color="{BLUE}"
        fontname="Helvetica"
        fontsize=10
        penwidth=1.6
    ];


    // -----------------------------------------------------------------------
    // Customer (customers_dim.csv, built from studentInfo.csv)
    // -----------------------------------------------------------------------

    Customer [label=<
        <table border="0" cellborder="1" cellspacing="0" cellpadding="5">

            <tr>
                <td bgcolor="{LIGHT}">
                    <b>Customer</b><br/>
                    <font point-size="9">
                        Entity · customers_dim.csv · 28,785 rows
                    </font>
                </td>
            </tr>

            <tr>
                <td align="left">
                    <b>id_student : Int «PK»</b>
                </td>
            </tr>

            <tr>
                <td align="left">gender : String</td>
            </tr>

            <tr>
                <td align="left">highest_education : String</td>
            </tr>

            <tr>
                <td align="left">imd_band : String</td>
            </tr>

            <tr>
                <td align="left">disability : String</td>
            </tr>

            <tr>
                <td align="left" bgcolor="#FFF2CC">
                    region : String <b>«partitionKey»</b>
                </td>
            </tr>

        </table>
    >];


    // -----------------------------------------------------------------------
    // Assessment (studentAssessment.csv) - plays the Transaction/Event role
    // -----------------------------------------------------------------------

    Transaction [label=<
        <table border="0" cellborder="1" cellspacing="0" cellpadding="5">

            <tr>
                <td bgcolor="{LIGHT}">
                    <b>Assessment (Transaction)</b><br/>
                    <font point-size="9">
                        Event · studentAssessment.csv · 173,912 rows
                    </font>
                </td>
            </tr>

            <tr>
                <td align="left">
                    id_student : Int «FK»
                </td>
            </tr>

            <tr>
                <td align="left">
                    id_assessment : Int «FK»
                </td>
            </tr>

            <tr>
                <td align="left" bgcolor="#FFF2CC">
                    date_submitted : Int (day offset) <b>«eventTime»</b>
                </td>
            </tr>

            <tr>
                <td align="left">
                    is_banked : Boolean
                </td>
            </tr>

            <tr>
                <td align="left">
                    score : Decimal <b>«metric»</b>
                </td>
            </tr>

            <tr>
                <td align="left">
                    <font point-size="8">no surrogate PK - id_student and</font>
                </td>
            </tr>
            <tr>
                <td align="left">
                    <font point-size="8">id_assessment together are not unique</font>
                </td>
            </tr>

        </table>
    >];


    // -----------------------------------------------------------------------
    // Entitlement (entitlements_dim.csv, built from studentRegistration.csv)
    // -----------------------------------------------------------------------

    Entitlement [label=<
        <table border="0" cellborder="1" cellspacing="0" cellpadding="5">

            <tr>
                <td bgcolor="{LIGHT}">
                    <b>Entitlement</b><br/>
                    <font point-size="9">
                        Entity · entitlements_dim.csv · 28,785 rows
                    </font>
                </td>
            </tr>

            <tr>
                <td align="left">
                    <b>id_student : Int «PK,FK»</b>
                </td>
            </tr>

            <tr>
                <td align="left">
                    date_registration : Int (day offset)
                </td>
            </tr>

            <tr>
                <td align="left">
                    date_unregistration : Int (day offset)
                </td>
            </tr>

        </table>
    >];


    // -----------------------------------------------------------------------
    // Assessment definition (assessment_defs.csv, from assessments.csv)
    // -----------------------------------------------------------------------

    Config [label=<
        <table border="0" cellborder="1" cellspacing="0" cellpadding="5">

            <tr>
                <td bgcolor="#F2F2F2">
                    <b>AssessmentDef (Config)</b><br/>
                    <font point-size="9">
                        Lookup · assessment_defs.csv · 206 rows
                    </font>
                </td>
            </tr>

            <tr>
                <td align="left">
                    <b>id_assessment : Int «PK»</b>
                </td>
            </tr>

            <tr>
                <td align="left">
                    assessment_type : String
                </td>
            </tr>

            <tr>
                <td align="left">
                    date : Int (day offset)
                </td>
            </tr>

            <tr>
                <td align="left">
                    weight : Decimal
                </td>
            </tr>

        </table>
    >];


    // -----------------------------------------------------------------------
    // Relationships
    // -----------------------------------------------------------------------

    // One customer submits many assessments - the genuine 1..* basis.
    Customer -> Transaction [
        taillabel="1"
        headlabel="0..*"
        label="submits"
        penwidth=2.4
        color="{AMBER}"
        labeldistance=2.2
        labelangle=18
        arrowhead=none
    ];


    // id_student is unique in entitlements_dim: 1:1 extension, not 1..*.
    Customer -> Entitlement [
        taillabel="1"
        headlabel="1"
        label="registered as"
        style=dashed
        labeldistance=2.2
        labelangle=18
        arrowhead=none
    ];


    // Each assessment definition applies to many submissions.
    Config -> Transaction [
        taillabel="1"
        headlabel="0..*"
        label="defines"
        labeldistance=2.2
        labelangle=18
        arrowhead=none
    ];


    // -----------------------------------------------------------------------
    // Notes
    // -----------------------------------------------------------------------

    note1 [
        shape=note
        style=filled
        fillcolor="#FFF9E6"
        color="{AMBER}"
        fontsize=10
        align=left
        label=<
            <b>Partition key: region</b><br align="left"/>
            13 distinct values<br align="left"/>
            7,341 / 13,049 / 18,263 records<br align="left"/>
            skew ratio 2.49 : 1 (measured)<br align="left"/>
            <br align="left"/>
            <b>id_student rejected:</b><br align="left"/>
            23,369 distinct values, close to the<br align="left"/>
            173,912-row dataset size - an event<br align="left"/>
            identifier, not a business grouping<br align="left"/>
            attribute (also skewed, 28:1, but<br align="left"/>
            rejected on grounds of role, not skew).
        >
    ];


    note2 [
        shape=note
        style=filled
        fillcolor="#F2F2F2"
        color="{GREY}"
        fontsize=10
        align=left
        label=<
            <b>Lookup (206 rows)</b><br align="left"/>
            Does not count towards the<br align="left"/>
            three-file minimum.<br align="left"/>
            Broadcast at join time.
        >
    ];


    note1 -> Customer [style=invis];
    note2 -> Config [style=invis];

    {{ rank=same; note1; Customer; }}
    {{ rank=same; note2; Config; }}
}}
"""


# ---------------------------------------------------------------------------
# 2. Session 1 architecture (Part 11)
# ---------------------------------------------------------------------------

ARCHITECTURE = f"""
digraph Architecture {{

    rankdir=LR;
    bgcolor="white";
    compound=true;

    nodesep=0.4;
    ranksep=0.9;

    fontname="Helvetica";
    labelloc="t";
    fontsize=17;

    label=<<b>CMA-Flow — Session 1 Ingestion and Parallel-Compute Layer</b><br/>
    <font point-size="11">
    actual repository file names ·
    PySpark local mode · bounded parallelism = 4
    </font><br/> >;


    node [
        shape=box
        style="rounded,filled"
        fontname="Helvetica"
        fontsize=10
        penwidth=1.3
        margin="0.16,0.10"
    ];

    edge [
        color="{BLUE}"
        penwidth=1.4
        fontname="Helvetica"
        fontsize=9
    ];


    // -----------------------------------------------------------------------
    // Raw OULAD source files
    // -----------------------------------------------------------------------

    subgraph cluster_raw {{

        label=<<b>Raw OULAD Files</b><br/>
        <font point-size="9">Datasets/</font>>;

        fontsize=11;
        color="{GREY}";
        style=dashed;
        fontname="Helvetica";

        raw_si [
            label="studentInfo.csv\\n32,593 rows"
            fillcolor="white"
            color="{GREY}"
        ];

        raw_sr [
            label="studentRegistration.csv\\n32,593 rows"
            fillcolor="white"
            color="{GREY}"
        ];

        raw_a [
            label="assessments.csv\\n206 rows"
            fillcolor="white"
            color="{GREY}"
        ];
    }}


    // -----------------------------------------------------------------------
    // Prep step (this dataset's extra stage vs. the original template)
    // -----------------------------------------------------------------------

    prep [
        label="prep_oulad.py\\ndedupe to student grain"
        fillcolor="#FCE4D6"
        color="{AMBER}"
    ];


    // -----------------------------------------------------------------------
    // Prepared source files
    // -----------------------------------------------------------------------

    subgraph cluster_source {{

        label=<<b>Prepared Files</b><br/>
        <font point-size="9">Datasets/ (built by prep_oulad.py)</font>>;

        fontsize=11;
        color="{GREY}";
        style=dashed;
        fontname="Helvetica";


        tx [
            label="studentAssessment.csv\\n173,912 rows · Event"
            fillcolor="{LIGHT}"
            color="{BLUE}"
        ];

        cust [
            label="customers_dim.csv\\n28,785 rows · Entity"
            fillcolor="{LIGHT}"
            color="{BLUE}"
        ];

        ent [
            label="entitlements_dim.csv\\n28,785 rows · Entity"
            fillcolor="{LIGHT}"
            color="{BLUE}"
        ];

        conf [
            label="assessment_defs.csv\\n206 rows · Lookup"
            fillcolor="#F2F2F2"
            color="{GREY}"
        ];
    }}


    // -----------------------------------------------------------------------
    // Ingestion
    // -----------------------------------------------------------------------

    subgraph cluster_ingest {{

        label=<<b>Ingestion</b><br/>
        <font point-size="9">session1_parallel_compute/</font>>;

        fontsize=11;
        color="{GREY}";
        style=dashed;
        fontname="Helvetica";


        profile [
            label="profile_files.py\\neligibility + inventory"
            fillcolor="#FFF2CC"
            color="{AMBER}"
        ];

        join [
            label="load_and_join.py\\nbroadcast joins\\n173,912 → 173,912"
            fillcolor="#FFF2CC"
            color="{AMBER}"
        ];
    }}


    // -----------------------------------------------------------------------
    // Parallel compute
    // -----------------------------------------------------------------------

    subgraph cluster_compute {{

        label=<<b>Parallel Compute</b><br/>
        <font point-size="9">PySpark · local mode</font>>;

        fontsize=11;
        color="{GREY}";
        style=dashed;
        fontname="Helvetica";


        repart [
            label="repartition(4, 'region')\\nbounded parallelism"
            fillcolor="#E2EFDA"
            color="#548235"
        ];

        agg [
            label="parallel_compute.py\\ngroupBy(region)\\ncount · sum · avg(score)"
            fillcolor="#E2EFDA"
            color="#548235"
        ];

        base [
            label="sequential_baseline.py\\npandas reference"
            fillcolor="#FCE4D6"
            color="{AMBER}"
        ];

        valid [
            label="validate()\\n13 groups · Δ = 0.0"
            fillcolor="#FCE4D6"
            color="{AMBER}"
        ];
    }}


    // -----------------------------------------------------------------------
    // Session 1 output
    // -----------------------------------------------------------------------

    subgraph cluster_out {{

        label=<<b>Session 1 Output</b><br/>
        <font point-size="9">results/</font>>;

        fontsize=11;
        color="{GREY}";
        style=dashed;
        fontname="Helvetica";


        parquet [
            label="regional_score_summary.parquet\\n13 rows · region,\\ntxn_count,\\nscore_total, score_mean"
            fillcolor="{LIGHT}"
            color="{NAVY}"
            penwidth=2.2
        ];

        bench [
            label="session1_benchmark.csv"
            fillcolor="white"
            color="{GREY}"
        ];

        parts [
            label="partition_sizes.csv"
            fillcolor="white"
            color="{GREY}"
        ];
    }}


    // -----------------------------------------------------------------------
    // Session 2
    // -----------------------------------------------------------------------

    s2 [
        label="Session 2\\nreconciles against\\nregional_score_summary"
        shape=box
        style="rounded,dashed,filled"
        fillcolor="white"
        color="{NAVY}"
        fontsize=10
    ];


    // -----------------------------------------------------------------------
    // Data flow
    // -----------------------------------------------------------------------

    raw_si -> prep;
    raw_sr -> prep;
    raw_a -> prep [style=dotted];

    prep -> tx [style=dotted, label="passthrough"];
    prep -> cust;
    prep -> ent;
    prep -> conf;

    tx -> profile;

    cust -> profile [style=dotted];
    ent -> profile [style=dotted];
    conf -> profile [style=dotted];

    profile -> join [label="eligible"];

    join -> repart;

    join -> base [label="same joined data"];

    repart -> agg;

    agg -> valid;

    base -> valid [label="reference"];

    valid -> parquet [
        label="passed"
        color="#548235"
        penwidth=2.0
    ];

    agg -> bench [style=dotted];

    repart -> parts [style=dotted];

    parquet -> s2 [
        style=dashed
        color="{NAVY}"
        penwidth=1.8
    ];
}}
"""


# ---------------------------------------------------------------------------
# Rendering function
# ---------------------------------------------------------------------------

def render(dot_source: str, out_png: Path) -> None:
    """
    Write DOT source to a temporary .dot file,
    render it using Graphviz,
    then remove the temporary file.
    """

    dot_file = out_png.with_suffix(".dot")

    dot_file.write_text(
        dot_source,
        encoding="utf-8"
    )

    subprocess.run(
        [
            "dot",
            "-Tpng",
            "-Gdpi=150",
            str(dot_file),
            "-o",
            str(out_png),
        ],
        check=True,
    )

    dot_file.unlink()

    print(f"Wrote {out_png}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:

    render(
        ENTITY,
        DOCS / "entity-model-session1.png"
    )

    render(
        ARCHITECTURE,
        ARCH / "architecture-session1.png"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())