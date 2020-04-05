# subscene-dl changelog

## HEAD

- Fixed crash when parsing subscene movie pages with inline-ads along
  with the subtitles
- Subtitles with a 'Bad' rating no longer raise a parsing error
- Rename subscene html parsing module from parser to htmlparse due to a
  naming conflict with internal Python's modules
- Add two modules:`subscene.api` and `subscene.cli`. The api modules
  exposes the data from the underling parsing of the subscene website into a simple
  API which is in turn used by the cli module to choose the most
  appropriate subtitle from the matches subtitles.
