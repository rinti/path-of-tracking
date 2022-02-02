from pob_gen import PobGen

acc = "comoestoy"
char = "ChaseUniqueChaser"

pob = PobGen.from_poe_profile(acc, char)
pob.write_xml()

# pob_profile_to_pob_code(fetch_items(acc, char), fetch_passives(acc, char))
