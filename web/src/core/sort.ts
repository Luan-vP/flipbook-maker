function naturalKey(name: string): (string | number)[] {
  return name.split(/(\d+)/).map((part) =>
    /^\d+$/.test(part) ? parseInt(part, 10) : part.toLowerCase(),
  );
}

export function naturalSort(names: string[]): string[] {
  return [...names].sort((a, b) => {
    const ka = naturalKey(a);
    const kb = naturalKey(b);
    for (let i = 0; i < Math.min(ka.length, kb.length); i++) {
      const pa = ka[i];
      const pb = kb[i];
      if (pa < pb) return -1;
      if (pa > pb) return 1;
    }
    return ka.length - kb.length;
  });
}
