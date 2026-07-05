(parser-framework)=

# Framework: Add and extend URL parsers - `libvcs.url.base`

Most readers can use the stock Git, Mercurial, and Subversion parsers. Reach
for this lower-level framework when you need a custom URL shape: define a
{class}`~libvcs.url.base.Rule`, group rules in a
{class}`~libvcs.url.base.RuleMap`, and attach that map to a parser class.

```{eval-rst}
.. automodule:: libvcs.url.base
   :members:
   :undoc-members:
```
