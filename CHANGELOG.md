# subscene-dl changelog

## HEAD

- Fixed crash when parsing subscene movie pages with inline-ads along
  with the subtitles
- Subtitles with a 'Bad' rating no longer raise a parsing error
- Rename subscene html parsing module from parser to htmlparse due to a
  naming conflict with internal Python's modules
