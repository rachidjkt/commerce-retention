# Attribution and license scope

## Dataset

Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. [doi:10.24432/C5BW33](https://doi.org/10.24432/C5BW33). The [dataset page](https://archive.ics.uci.edu/dataset/352/online-retail) identifies [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) terms. The workbook is downloaded separately; source-row preservation, filtering, order aggregation, and snapshot construction are documented in the README and SQL. Dataset terms do not license this repository's code.

## Code and dependencies

The available repository history begins at `4762dd5`, packaging the existing local project. Source headers and that history do not identify copied third-party application code or include a separate upstream application notice. This is a review of the available source/history, not a claim to have established every pre-repository contribution's authorship.

The implementation imports dependencies rather than vendoring their source. `requirements.txt` is the complete historical environment freeze; installation brings each package's own licenses and notices. Principal upstream projects are [DuckDB](https://github.com/duckdb/duckdb), [dbt Core](https://github.com/dbt-labs/dbt-core), [dbt-duckdb](https://github.com/duckdb/dbt-duckdb), [pandas](https://github.com/pandas-dev/pandas), [scikit-learn](https://github.com/scikit-learn/scikit-learn), [NumPy](https://github.com/numpy/numpy), [joblib](https://github.com/joblib/joblib), and [openpyxl](https://openpyxl.readthedocs.io/).

No models, weights, workbook, database, or customer-level outputs are distributed. The two committed metric CSVs are aggregate experiment outputs. No project-wide code license is added without an owner-selected license and authority to grant it; dependency and dataset licenses remain separate.
