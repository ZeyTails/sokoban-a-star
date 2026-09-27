/* -------------------------------------------------------
   Sokoban en PROLOG : modelisation par faits et regles
   ------------------------------------------------------- */

/* ======================
   1) FAITS (le niveau)
   ====================== */

% Grille 7x7, murs exterieurs.
mur(p(X,1)) :- between(1,7,X).
mur(p(X,7)) :- between(1,7,X).
mur(p(1,Y)) :- between(1,7,Y).
mur(p(7,Y)) :- between(1,7,Y).

% Mur interne (exemple).
mur(p(4,4)).

% Cibles (docks).
cible(p(5,3)).
cible(p(5,5)).

% Etat initial.
joueur_init(p(2,3)).
caisse_init(p(3,3)).
caisse_init(p(3,5)).

/* ======================
   2) REPRESENTATION ETAT
   ====================== */

% etat(Joueur, ListeCaisses)
etat_initial(etat(Joueur, CaissesTriees)) :-
    joueur_init(Joueur),
    findall(C, caisse_init(C), Caisses),
    sort(Caisses, CaissesTriees).

/* ======================
   3) REGLES DE MOUVEMENT
   ====================== */

dir(haut,   0, -1).
dir(bas,    0,  1).
dir(gauche,-1,  0).
dir(droite, 1,  0).

avance(p(X,Y), DX, DY, p(X2,Y2)) :-
    X2 is X + DX,
    Y2 is Y + DY.

occupe(P, Caisses) :-
    member(P, Caisses).

libre(P, Caisses) :-
    \+ mur(P),
    \+ occupe(P, Caisses).

% Regle principale : deplacer un etat selon une action.
deplacer(etat(J, Caisses), Action, etat(J2, Caisses2)) :-
    dir(Action, DX, DY),
    avance(J, DX, DY, J2),
    (
        % Cas 1 : devant le joueur il y a une caisse, on pousse.
        occupe(J2, Caisses) ->
            avance(J2, DX, DY, Pousse),
            \+ mur(Pousse),
            select(J2, Caisses, Rest),
            \+ occupe(Pousse, Rest),
            sort([Pousse|Rest], Caisses2)
        ;
        % Cas 2 : case libre, le joueur avance simplement.
        libre(J2, Caisses),
        Caisses2 = Caisses
    ).

/* ======================
   4) TEST DE BUT
   ====================== */

gagne(etat(_, Caisses)) :-
    forall(cible(C), member(C, Caisses)).

/* ======================
   5) RESOLUTION (DFS BORNE)
   ====================== */

% resoudre(+ProfondeurMax, -Plan)
% Cherche une suite d'actions qui mene a l'etat but.
resoudre(ProfondeurMax, Plan) :-
    etat_initial(E0),
    dfs_borne(E0, [E0], ProfondeurMax, Plan).

dfs_borne(E, _, _, []) :-
    gagne(E), !.

dfs_borne(E, Visites, D, [A|Suite]) :-
    D > 0,
    deplacer(E, A, E2),
    \+ member(E2, Visites),
    D2 is D - 1,
    dfs_borne(E2, [E2|Visites], D2, Suite).

/* ======================
   6) EXEMPLES DE REQUETES
   ======================

?- etat_initial(E).
?- deplacer(etat(p(2,3), [p(3,3),p(3,5)]), droite, E2).
?- resoudre(20, Plan).

*/
