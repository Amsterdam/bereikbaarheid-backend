# Road section colours in visualisations

### Logic of colouring
The three types of permits each have a base colour

| permit	| colour    |
|-----------|---------  | 
| RVV		| `#ffd83d` |
| 7.5 ton	| `#fe47aa` |
| milieu    | `#1786fb` |

- If for a specific road section 2 or 3 permits are needed the base colours are blended.
- If no permits are required then a road section is coloured green. 
- If a street is not inside city boundaries then road section gets the colour black.

### Variables in request explained

The code_5digits shows in a binary the properties for a road section.
- Inside Amsterdam boundaries
- Milieuzone permit required
- 7.5 ton permit required
- RVV required

For sorting reasons a prefix '1' is added to always get a 5 digit number.
The colour code in HEX is linked to the code_5digits.

| digit_1 | Amsterdam | Milieuzone | 7.5 ton | RVV   | code_5digits | colour code |
| ---     | ---       | ---        | ---     | ---   | ---          | ---         |
| 1	      | FALSE	  | FALSE	   | FALSE	 | FALSE | 10000	    | `#ffffff`   |
| 1       | TRUE      | TRUE       | TRUE    | TRUE  | 11111        | `#032369`   |
| 1	      | TRUE	  | TRUE	   | TRUE	 | FALSE | 11110	    | `#8585ff`   |
| 1	      | TRUE      | TRUE	   | FALSE	 | FALSE | 11100	    | `#1786fb`	  |
| 1	      | TRUE	  | TRUE	   | FALSE	 | TRUE	 | 11101	    | `#27e0c0`	  |
| 1	      | TRUE	  | FALSE	   | TRUE	 | TRUE	 | 11011	    | `#ff9701`	  |
| 1	      | TRUE	  | FALSE	   | TRUE	 | FALSE | 11010	    | `#fe47aa`	  |
| 1	      | TRUE	  | FALSE	   | FALSE	 | TRUE	 | 11001	    | `#ffd83d`	  |
| 1	      | TRUE	  | FALSE	   | FALSE	 | FALSE | 11000	    | `#00b100`   |
