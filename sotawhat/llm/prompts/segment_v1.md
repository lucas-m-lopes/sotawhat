You split one AI newsletter e-mail into its stories for a personal insight engine. The text marks every link as "anchor text [n]", and the list of numbered URLs comes at the end.

Return every distinct story the newsletter covers (news, paper, model, tool, repository, opinion piece), at most 15, in the order they appear:
- title: a short headline in the newsletter's language; do not translate.
- summary: one to three sentences in the newsletter's own words; never add facts, numbers or names that are not in the text.
- link: the number n of the link that best points to the story's source (the paper, repository, model page, official blog post or product page), or 0 when there is none. Never choose unsubscribe, preferences, "view in browser", referral, social-media share or sponsor links.
- category: news · paper · model · tool · repo · opinion · event · job · sponsor · other. Use sponsor for ads and paid placements, job for job posts and event for webinars, courses and conferences.

Skip the greeting, the table of contents, referral programs, polls and footers.
