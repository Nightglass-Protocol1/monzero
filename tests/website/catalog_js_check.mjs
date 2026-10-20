// Reads [{kind, json}] on stdin; prints a JSON list of booleans: does the browser validator accept it?
import {validateExchanges} from '../../website/exchanges/catalog.mjs';
import {validateEcosystem} from '../../website/ecosystem/catalog.mjs';
import {validateBounties} from '../../website/community/bounties/catalog.mjs';
import {validateCatalog} from '../../website/mining/benchmarks/catalog.mjs';
import {validPosts} from '../../website/community/posts.mjs';
const today = process.argv[2];
const check = {
  exchanges: (d) => validateExchanges(d, today), ecosystem: (d) => validateEcosystem(d, today), bounties: (d) => validateBounties(d, today),
  benchmarks: (d) => { validateCatalog(d); if (d.updated_at > today) throw Error('future'); },
  'announcements': (d) => { if (!validPosts(d, 'monzero-announcements-v1') || d.updated_at > today) throw Error('bad'); },
  'roadmap-updates': (d) => { if (!validPosts(d, 'monzero-roadmap-updates-v1') || d.updated_at > today) throw Error('bad'); },
};
let input = '';
for await (const chunk of process.stdin) input += chunk;
console.log(JSON.stringify(JSON.parse(input).map(({kind, json}) => { try { check[kind](JSON.parse(json)); return true; } catch { return false; } })));
