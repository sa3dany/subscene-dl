# subscene-dl changelog

## HEAD

### Changes

- Support all languages on subscene.com not just the popular ones. There
  are some exceptions though which are explained in the notes section
  below

- CLI `file` parameter now expects a media file instead of just a movie title.
  The subtitle files are now saved to the same directory as the passed
  media file instead of the current working directory

### Notes

Some `languages` on subscene are not actually languages. For example,
`Big 5 code` is and Chinese Character encoding method. I've opted not to
support these at the moment. The full list of non-supported
`languages`along with their corresponding numeric ID are:

- Big 5 code (3) (encoding method)
- Bulgarian/ English (6) (multiple subtitles in a single zip)
- Chinese BG code (7) (encoding method)
- Dutch/ English (12) (multiple subtitles in a single zip)
- English/ German (15) (multiple subtitles in a single zip)
- Hungarian/ English (24) (multiple subtitles in a single zip)

## 0.1

- Add two modules:`subscene.api` and `subscene.cli`. The api modules
  exposes the data from the underling parsing of the subscene website into a simple
  API which is in turn used by the cli module to choose the most
  appropriate subtitle from the matches subtitles.
- Rename subscene html parsing module from parser to htmlparse due to a
  naming conflict with internal Python's modules
- Fixed crash when parsing subscene movie pages with inline-ads along
  with the subtitles
- Subtitles with a 'Bad' rating no longer raise a parsing error
