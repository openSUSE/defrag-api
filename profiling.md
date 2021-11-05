## Profiling
The application supports profiling-on-tests out of the box:

1. Make sure you have `graphviz` installed. Reference: https://www.graphviz.org/.
   - NB: No Python interface with this library is required. Not satisfying this dependency is likely to cause a "Broken pipe" error when running the command below.
2. Run the tests with the appropriate flags, for example:
    ```
    pytest defrag/tests/unittests/test_suggestions.py --profile --profile-svg
    ```
    will write to disk profiling results, along with a nice SVG graph. (By default outputs can be found under `./prof`.)