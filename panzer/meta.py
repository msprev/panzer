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
    # 2. Update with values in fields for additive lists
    old = update_additive_lists(old, new)
    # 3. 'template' field
    if 'template' in new:
        old['template'] = new['template']
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
    elif field_type == 'MetaList':
        content = list()
        for content_raw in get_content(metadata, field, 'MetaList'):
            content.append(pandocfilters.stringify(content_raw))
        return content
    else:
        raise error.WrongType('"%s" value must be of type "MetaInlines"'
                              'or "MetaList"' % field)

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
                if len(args_content) != 1:
                    raise error.BadArgsFormat
                if args_content[0][const.T] != 'Code':
                    raise error.BadArgsFormat
                arguments_raw = args_content[0][const.C][1]
                entry['arguments'] = shlex.split(arguments_raw)
            except error.BadArgsFormat:
                info.log('ERROR', 'panzer', 'Cannot read "args" of "%s" --- '
                         'should be formatted: args: "`--arguments`"'
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
