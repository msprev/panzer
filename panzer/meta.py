""" Functions for manipulating metadata """
import pandocfilters
import shlex
from . import const
from . import info
from . import util
from . import error

def update_metadata(old, new):
    """ return old updated with new metadata """
    # 1. Update with values in 'metadata' field
    try:
        old.update(get_content(new, 'metadata', 'MetaMap'))
    except (error.MissingField, KeyError):
        pass
    except error.WrongType as err:
        info.log('WARNING', 'panzer', err)
    # 2. Update with values in 'commandline' field
    old = update_commandline(old, new)
    # 3. Update with values in fields for additive lists
    old = update_additive_lists(old, new)
    # 4. Update 'template' field
    if 'template' in new:
        old['template'] = new['template']
    return old

def update_commandline(old, new):
    """ return old updated with info from `commandline` in new """
    try:
        try:
            new_commandline = get_content(new, 'commandline', 'MetaMap')
        except error.MissingField:
            # field not in incoming metadata, quit
            return old
        try:
            old_commandline = get_content(old, 'commandline', 'MetaMap')
        except error.MissingField:
            # field not in old metadata, start with an empty dict
            old_commandline = dict()
    except error.WrongType as err:
        # wrong type of value under field, quit
        info.log('WARNING', 'panzer', err)
        return old
    old_commandline.update(new_commandline)
    if old_commandline == dict():
        # if still empty, don't bother adding it
        return old
    set_content(old, 'commandline', old_commandline, 'MetaMap')
    return old

def update_additive_lists(old, new):
    """ return old updated with info from additive lists in new """
    for field in const.RUNLIST_KIND:
        try:
            try:
                new_list = get_content(new, field, 'MetaList')
            except error.MissingField:
                # field not in incoming metadata, move to next list
                continue
            try:
                old_list = get_content(old, field, 'MetaList')
            except error.MissingField:
                # field not in old metadata, start with an empty list
                old_list = list()
        except error.WrongType as err:
            # wrong type of value under field, skip to next list
            info.log('WARNING', 'panzer', err)
            continue
        old_list.extend(new_list)
        set_content(old, field, old_list, 'MetaList')
    return old

def apply_kill_rules(old_list):
    """ return old_list after applying kill rules """
    new_list = list()
    for item in old_list:
        # 1. Sanity checks
        check_c_and_t_exist(item)
        item_content = item[const.C]
        item_type = item[const.T]
        if item_type != 'MetaMap':
            info.log('ERROR', 'panzer',
                     'fields "' + '", "'.join(const.RUNLIST_KIND) + '" '
                     'value must be of type "MetaMap"---ignoring 1 item')
            continue
        if len(item_content.keys() & {'run', 'kill', 'killall'}) != 1:
            info.log('ERROR', 'panzer',
                     'must contain exactly one "run", "kill", '
                     'or "killall" per item---ignoring 1 item')
            continue
        # 2. Now operate on content
        if 'run' in item_content:
            if get_type(item_content, 'run') != 'MetaInlines':
                info.log('ERROR', 'panzer',
                         '"run" value must be of type "MetaInlines"'
                         '---ignoring 1 item')
                continue
            new_list.append(item)
        elif 'kill' in item_content:
            try:
                to_be_killed = get_content(item_content, 'kill', 'MetaInlines')
            except error.WrongType as err:
                info.log('WARNING', 'panzer', err)
                continue
            new_list = [i for i in new_list
                        if get_content(i[const.C],
                                       'run',
                                       'MetaInlines') != to_be_killed]
        elif 'killall' in item_content:
            try:
                if get_content(item_content, 'killall', 'MetaBool') == True:
                    new_list = list()
            except error.WrongType as err:
                info.log('WARNING', 'panzer', err)
                continue
        else:
            # Should never occur, caught by previous syntax check
            continue
    return new_list

def get_nested_content(metadata, fields, expected_type_of_leaf=None):
    """ return content of field by traversing a list of MetaMaps

    args:
        metadata : dictionary to traverse
        fields       : list of fields to traverse in dictionary from
        shallowest to deepest. Content of every field, except the last,
        must be type 'MetaMap' (otherwise fields could not be traversed).
        The content of final field in the list is returned.
        expected_type_of_leaf : (optional) expected type of final field's
        content

    Returns:
        content of final field in list, or the empty dict ({}) if field of
        expected type is not found
    """
    current_field = fields.pop(0)
    try:
        # If on a branch...
        if fields:
            next_content = get_content(metadata, current_field, 'MetaMap')
            return get_nested_content(next_content, fields,
                                      expected_type_of_leaf)
        # Else on a leaf...
        else:
            return get_content(metadata, current_field, expected_type_of_leaf)
    except error.MissingField:
        # current_field not found, return {}: nothing to update
        return dict()
    except error.WrongType as err:
        info.log('WARNING', 'panzer', err)
        # wrong type found, return {}: nothing to update
        return dict()

def get_content(metadata, field, expected_type=None):
    """ return content of field """
    if field not in metadata:
        raise error.MissingField('field "%s" not found' % field)
    check_c_and_t_exist(metadata[field])
    if expected_type:
        found_type = metadata[field][const.T]
        if found_type != expected_type:
            raise error.WrongType('value of "%s": expecting type "%s", '
                                  'but found type "%s"'
                                  % (field, expected_type, found_type))
    return metadata[field][const.C]

def get_type(metadata, field):
    """ return type of field """
    if field not in metadata:
        raise error.MissingField('field "%s" not found' % field)
    check_c_and_t_exist(metadata[field])
    return metadata[field][const.T]

def set_content(metadata, field, content, content_type):
    """ set content and type of field in metadata """
    metadata[field] = {const.C: content, const.T: content_type}

def get_list_or_inline(metadata, field):
    """ return content of MetaList or MetaInlines item coerced as list """
    field_type = get_type(metadata, field)
    if field_type == 'MetaInlines':
        content_raw = get_content(metadata, field, 'MetaInlines')
        content = [pandocfilters.stringify(content_raw)]
        return content
    elif field_type == 'MetaString':
        content_raw = get_content(metadata, field, 'MetaString')
        content = [content_raw]
        return content
    elif field_type == 'MetaList':
        content = list()
        for content_raw in get_content(metadata, field, 'MetaList'):
            content.append(pandocfilters.stringify(content_raw))
        return content
    else:
        raise error.WrongType('"%s" value must be of type "MetaInlines", '
                              '"MetaList", or "MetaString"' % field)

def get_metadata(ast):
    """ returns metadata branch of ast or {} if not present """
    try:
        metadata = ast[0]['unMeta']
    except KeyError:
        metadata = dict()
    return metadata

def get_runlist(metadata, kind, options):
    """ return run list for kind from metadata """
    runlist = list()
    # - return empty list unless entries of kind are in metadata
    try:
        metadata_list = get_content(metadata, kind, 'MetaList')
    except (error.WrongType, error.MissingField) as err:
        info.log('WARNING', 'panzer', err)
        return runlist
    for item in metadata_list:
        check_c_and_t_exist(item)
        item_content = item[const.C]
        # - create new entry
        entry = dict()
        entry['kind'] = kind
        entry['command'] = str()
        entry['status'] = const.QUEUED
        # - get entry command
        command_raw = get_content(item_content, 'run', 'MetaInlines')
        command_str = pandocfilters.stringify(command_raw)
        entry['command'] = util.resolve_path(command_str, kind, options)
        # - get entry arguments
        entry['arguments'] = list()
        if 'args' in item_content:
            try:
                if get_type(item_content, 'args') != 'MetaInlines':
                    raise error.BadArgsFormat
                args_content = get_content(item_content, 'args', 'MetaInlines')
                if len(args_content) != 1 \
                or args_content[0][const.T] != 'Code':
                    raise error.BadArgsFormat
                arguments_raw = args_content[0][const.C][1]
                entry['arguments'] = shlex.split(arguments_raw)
            except error.BadArgsFormat:
                info.log('ERROR', 'panzer', 'Cannot read "args" of "%s". '
                         'Syntax should be args: "`--ARGUMENTS`"'
                         % command_str)
                entry['arguments'] = list()
        runlist.append(entry)
    return runlist

def check_c_and_t_exist(item):
    """ check item contains both C and T fields """
    if const.C not in item:
        message = 'Value of "%s" corrupt: "C" field missing' % repr(item)
        raise error.BadASTError(message)
    if const.T not in item:
        message = 'Value of "%s" corrupt: "T" field missing' % repr(item)
        raise error.BadASTError(message)

def expand_style_hierarchy(stylelist, styledef):
    """ return stylelist expanded to include all parent styles """
    expanded_list = []
    for style in stylelist:
        if style not in styledef:
            # - style not in styledef tree
            info.log('ERROR', 'panzer',
                     'No style definition found for style "%s" --- ignoring it'
                     % style)
            continue
        defcontent = get_content(styledef, style, 'MetaMap')
        if 'parent' in defcontent:
            # - non-leaf node
            parents = get_list_or_inline(defcontent, 'parent')
            expanded_list.extend(expand_style_hierarchy(parents, styledef))
        expanded_list.append(style)
    return expanded_list

def build_cli_options(dic):
    """ return a list of command line options specified in the dictionary dic """
    cli = list()
    for opt in dic:
        if dic[opt] == None:
            pass
        elif dic[opt] == True:
            cli += ['--%s' % opt]
        elif type(dic[opt]) is str:
            cli += ['--%s=%s' % (opt, dic[opt])]
        elif type(dic[opt]) is list:
            for val in dic[opt]:
                cli += ['--%s=%s' % (opt, val[0])]
    return cli

def parse_commandline(metadata):
    """ return a dictiory of pandoc command line options by parsing
    `commandline` field in metadata; return None if `commandline` is absent in
    metadata
    """
    if 'commandline' not in metadata:
        return None
    field_type = get_type(metadata, 'commandline')
    if field_type != 'MetaMap':
        info.log('ERROR', 'panzer',
                 'Value of field "%s" should be of type "MetaMap"'
                 '---found value of type "%s", ignoring it'
                 % ('commandline', field_type))
        return None
    content = get_content(metadata, 'commandline')
    # 1. remove bad options from `commandline`
    bad_opts = list(const.PANDOC_BAD_COMMANDLINE)
    for key in content:
        if key in bad_opts:
            info.log('ERROR', 'panzer',
                     '"%s" forbidden entry in panzer "commandline" '
                     'map---ignoring' % key)
        if key not in const.PANDOC_OPT_PHASE:
            info.log('ERROR', 'panzer',
                     'do not recognise pandoc command line option "--%s" in "commandline" '
                     'map---ignoring' % key)
            bad_opts += key
    content = {key: content[key]
               for key in content
               if key not in bad_opts}
    # 2. parse remaining opts
    commandline = {'r': dict(), 'w': dict()}
    for key in content:
        # 1. extract value of field with name 'key'
        val = None
        val_t = get_type(content, key)
        val_c = get_content(content, key)
        # if value is 'false', ignore
        if val_c == False:
            continue
        # if value is 'true', add --OPTION
        elif val_t == 'MetaBool' and val_c == True \
            and key not in const.PANDOC_OPT_ADDITIVE:
            val = True
        # if value type is inline code, add --OPTION=VAL
        elif val_t == 'MetaInlines':
            if len(val_c) != 1 or val_c[0][const.T] != 'Code':
                info.log('ERROR', 'panzer',
                         'Cannot read option "%s" in "commandline" field. '
                         'Syntax should be OPTION: "`VALUE`"' % key)
                continue
            if key in const.PANDOC_OPT_ADDITIVE:
                val = [get_list_or_inline(content, key)]
            else:
                val = get_list_or_inline(content, key)[0]
        # if value type is list of inline codes, add repeated --OPTION=VAL
        elif val_t == 'MetaList' and key in const.PANDOC_OPT_ADDITIVE:
            errs = False
            for item in val_c:
                if item[const.T] != 'MetaInlines' \
                        or item[const.C][0][const.T] != 'Code':
                    info.log('ERROR', 'panzer',
                             'Cannot read option "%s" in "commandline" field. '
                             'Syntax should be - OPTION: "`VALUE`"' % key)
                    errs = True
            if not errs:
                val = [[x] for x in get_list_or_inline(content, key)]
            else:
                continue
        # otherwise, signal error
        else:
            info.log('ERROR', 'panzer',
                     'Cannot read entry "%s" with type "%s" in '
                     '"commandline"---ignoring' % (key, val_t))
            continue
        # 2. update commandline dictionary with key, val
        for phase in const.PANDOC_OPT_PHASE[key]:
            commandline[phase][key] = val
    return commandline

def update_pandoc_options(old, new):
    """ return dictionary of pandoc command line options 'old' updated with 'new'
    """
    for p in ['r', 'w']:
        for key in old[p]:
            if key in new[p]:
                # if not already set in old, then override with new
                if old[p][key] == None or old[p][key] == False:
                    old[p][key] = new[p][key]
                # if already set and a list, then add new at end of list
                elif type(old[p][key]) is list:
                    old[p][key].extend(new[p][key])
                # if already set and same as new, then just continue quietly
                elif old[p][key] == new[p][key]:
                    continue
                else:
                # warn if new being overriden by old
                    if type(old[p][key]) is bool:
                        message = "--%s" % key
                    elif type(old[p][key]) is str:
                        message = "--%s=%s" % (key, old[p][key])
                    info.log('WARNING', 'panzer',
                             'command line option "%s" overriding setting '
                             'in "commandline" metadata' % message)
    return old

