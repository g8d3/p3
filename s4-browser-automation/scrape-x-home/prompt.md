example: 

tape is 1,2,3,4
scrape 1,2,3,4
scroll
tape is 1,2,3,4,5
scrape 5
tape is 1,2,3,4,5,6
scrape 6
nothing else happens? then scroll more
tape is 1,2,3,4,5,6,7,8,9
scrape 7,8,9
say user asked for 20 tweets
scroll more
tape is 5,6,7,8,9,10,11,12,13
scrape 10 to 13
scroll more
unfortunately you scrolled to much now tape is 15,16,17,18,19,20,21,22
you need to make sure your latest scraped tweet is at the start of the tape
scroll back
tape is 13,14,15,16,17,18,19,20
scrape till 20
you are done

i.e. you need to make sure code does not lose track of the tape